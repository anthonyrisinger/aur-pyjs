# object_store.py -- Object store for git objects
# Copyright (C) 2008-2009 Jelmer Vernooij <jelmer@samba.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# or (at your option) a later version of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA  02110-1301, USA.


"""Git object store interfaces and implementation."""


import errno
import itertools
import os
import posixpath
import stat
import tempfile
import urllib2

from dulwich.errors import (
    NotTreeError,
    )
from dulwich.file import GitFile
from dulwich.objects import (
    Commit,
    ShaFile,
    Tag,
    Tree,
    hex_to_sha,
    sha_to_hex,
    hex_to_filename,
    S_ISGITLINK,
    object_class,
    )
from dulwich.pack import (
    Pack,
    PackData,
    ThinPackData,
    iter_sha1,
    load_pack_index,
    write_pack,
    write_pack_data,
    write_pack_index_v2,
    )

INFODIR = 'info'
PACKDIR = 'pack'


class BaseObjectStore(object):
    """Object store interface."""

    def determine_wants_all(self, refs):
        return [sha for (ref, sha) in refs.iteritems()
                if not sha in self and not ref.endswith("^{}")]

    def iter_shas(self, shas):
        """Iterate over the objects for the specified shas.

        :param shas: Iterable object with SHAs
        :return: Object iterator
        """
        return ObjectStoreIterator(self, shas)

    def contains_loose(self, sha):
        """Check if a particular object is present by SHA1 and is loose."""
        raise NotImplementedError(self.contains_loose)

    def contains_packed(self, sha):
        """Check if a particular object is present by SHA1 and is packed."""
        raise NotImplementedError(self.contains_packed)

    def __contains__(self, sha):
        """Check if a particular object is present by SHA1.

        This method makes no distinction between loose and packed objects.
        """
        return self.contains_packed(sha) or self.contains_loose(sha)

    @property
    def packs(self):
        """Iterable of pack objects."""
        raise NotImplementedError

    def get_raw(self, name):
        """Obtain the raw text for an object.

        :param name: sha for the object.
        :return: tuple with numeric type and object contents.
        """
        raise NotImplementedError(self.get_raw)

    def __getitem__(self, sha):
        """Obtain an object by SHA1."""
        type_num, uncomp = self.get_raw(sha)
        return ShaFile.from_raw_string(type_num, uncomp)

    def __iter__(self):
        """Iterate over the SHAs that are present in this store."""
        raise NotImplementedError(self.__iter__)

    def add_object(self, obj):
        """Add a single object to this object store.

        """
        raise NotImplementedError(self.add_object)

    def add_objects(self, objects):
        """Add a set of objects to this object store.

        :param objects: Iterable over a list of objects.
        """
        raise NotImplementedError(self.add_objects)

    def tree_changes(self, source, target, want_unchanged=False):
        """Find the differences between the contents of two trees

        :param object_store: Object store to use for retrieving tree contents
        :param tree: SHA1 of the root tree
        :param want_unchanged: Whether unchanged files should be reported
        :return: Iterator over tuples with (oldpath, newpath), (oldmode, newmode), (oldsha, newsha)
        """
        todo = set([(source, target, "")])
        while todo:
            (sid, tid, path) = todo.pop()
            if sid is not None:
                stree = self[sid]
            else:
                stree = {}
            if tid is not None:
                ttree = self[tid]
            else:
                ttree = {}
            for name, oldmode, oldhexsha in stree.iteritems():
                oldchildpath = posixpath.join(path, name)
                try:
                    (newmode, newhexsha) = ttree[name]
                    newchildpath = oldchildpath
                except KeyError:
                    newmode = None
                    newhexsha = None
                    newchildpath = None
                if (want_unchanged or oldmode != newmode or
                    oldhexsha != newhexsha):
                    if stat.S_ISDIR(oldmode):
                        if newmode is None or stat.S_ISDIR(newmode):
                            todo.add((oldhexsha, newhexsha, oldchildpath))
                        else:
                            # entry became a file
                            todo.add((oldhexsha, None, oldchildpath))
                            yield ((None, newchildpath), (None, newmode), (None, newhexsha))
                    else:
                        if newmode is not None and stat.S_ISDIR(newmode):
                            # entry became a dir
                            yield ((oldchildpath, None), (oldmode, None), (oldhexsha, None))
                            todo.add((None, newhexsha, newchildpath))
                        else:
                            yield ((oldchildpath, newchildpath), (oldmode, newmode), (oldhexsha, newhexsha))

            for name, newmode, newhexsha in ttree.iteritems():
                childpath = posixpath.join(path, name)
                if not name in stree:
                    if not stat.S_ISDIR(newmode):
                        yield ((None, childpath), (None, newmode), (None, newhexsha))
                    else:
                        todo.add((None, newhexsha, childpath))

    def iter_tree_contents(self, tree_id, include_trees=False):
        """Iterate the contents of a tree and all subtrees.

        Iteration is depth-first pre-order, as in e.g. os.walk.

        :param tree_id: SHA1 of the tree.
        :param include_trees: If True, include tree objects in the iteration.
        :return: Yields tuples of (path, mode, hexhsa) for objects in a tree.
        """
        todo = [('', stat.S_IFDIR, tree_id)]
        while todo:
            path, mode, hexsha = todo.pop()
            is_subtree = stat.S_ISDIR(mode)
            if not is_subtree or include_trees:
                yield path, mode, hexsha
            if is_subtree:
                entries = reversed(list(self[hexsha].iteritems()))
                for name, entry_mode, entry_hexsha in entries:
                    entry_path = posixpath.join(path, name)
                    todo.append((entry_path, entry_mode, entry_hexsha))

    def find_missing_objects(self, haves, wants, progress=None,
                             get_tagged=None):
        """Find the missing objects required for a set of revisions.

        :param haves: Iterable over SHAs already in common.
        :param wants: Iterable over SHAs of objects to fetch.
        :param progress: Simple progress function that will be called with
            updated progress strings.
        :param get_tagged: Function that returns a dict of pointed-to sha -> tag
            sha for including tags.
        :return: Iterator over (sha, path) pairs.
        """
        finder = MissingObjectFinder(self, haves, wants, progress, get_tagged)
        return iter(finder.next, None)

    def find_common_revisions(self, graphwalker):
        """Find which revisions this store has in common using graphwalker.

        :param graphwalker: A graphwalker object.
        :return: List of SHAs that are in common
        """
        haves = []
        sha = graphwalker.next()
        while sha:
            if sha in self:
                haves.append(sha)
                graphwalker.ack(sha)
            sha = graphwalker.next()
        return haves

    def get_graph_walker(self, heads):
        """Obtain a graph walker for this object store.

        :param heads: Local heads to start search with
        :return: GraphWalker object
        """
        return ObjectStoreGraphWalker(heads, lambda sha: self[sha].parents)

    def generate_pack_contents(self, have, want, progress=None):
        """Iterate over the contents of a pack file.

        :param have: List of SHA1s of objects that should not be sent
        :param want: List of SHA1s of objects that should be sent
        :param progress: Optional progress reporting method
        """
        return self.iter_shas(self.find_missing_objects(have, want, progress))

    def peel_sha(self, sha):
        """Peel all tags from a SHA.

        :param sha: The object SHA to peel.
        :return: The fully-peeled SHA1 of a tag object, after peeling all
            intermediate tags; if the original ref does not point to a tag, this
            will equal the original SHA1.
        """
        obj = self[sha]
        obj_class = object_class(obj.type_name)
        while obj_class is Tag:
            obj_class, sha = obj.object
            obj = self[sha]
        return obj


class PackBasedObjectStore(BaseObjectStore):

    def __init__(self):
        self._pack_cache = None

    def contains_packed(self, sha):
        """Check if a particular object is present by SHA1 and is packed."""
        for pack in self.packs:
            if sha in pack:
                return True
        return False

    def _load_packs(self):
        raise NotImplementedError(self._load_packs)

    def _pack_cache_stale(self):
        """Check whether the pack cache is stale."""
        raise NotImplementedError(self._pack_cache_stale)

    def _add_known_pack(self, pack):
        """Add a newly appeared pack to the cache by path.

        """
        if self._pack_cache is not None:
            self._pack_cache.append(pack)

    @property
    def packs(self):
        """List with pack objects."""
        if self._pack_cache is None or self._pack_cache_stale():
            self._pack_cache = self._load_packs()
        return self._pack_cache

    def _iter_loose_objects(self):
        """Iterate over the SHAs of all loose objects."""
        raise NotImplementedError(self._iter_loose_objects)

    def _get_loose_object(self, sha):
        raise NotImplementedError(self._get_loose_object)

    def _remove_loose_object(self, sha):
        raise NotImplementedError(self._remove_loose_object)

    def pack_loose_objects(self):
        """Pack loose objects.
        
        :return: Number of objects packed
        """
        objects = set()
        for sha in self._iter_loose_objects():
            objects.add((self._get_loose_object(sha), None))
        self.add_objects(objects)
        for obj, path in objects:
            self._remove_loose_object(obj.id)
        return len(objects)

    def __iter__(self):
        """Iterate over the SHAs that are present in this store."""
        iterables = self.packs + [self._iter_loose_objects()]
        return itertools.chain(*iterables)

    def contains_loose(self, sha):
        """Check if a particular object is present by SHA1 and is loose."""
        return self._get_loose_object(sha) is not None

    def get_raw(self, name):
        """Obtain the raw text for an object.

        :param name: sha for the object.
        :return: tuple with numeric type and object contents.
        """
        if len(name) == 40:
            sha = hex_to_sha(name)
            hexsha = name
        elif len(name) == 20:
            sha = name
            hexsha = None
        else:
            raise AssertionError
        for pack in self.packs:
            try:
                return pack.get_raw(sha)
            except KeyError:
                pass
        if hexsha is None:
            hexsha = sha_to_hex(name)
        ret = self._get_loose_object(hexsha)
        if ret is not None:
            return ret.type_num, ret.as_raw_string()
        raise KeyError(hexsha)

    def add_objects(self, objects):
        """Add a set of objects to this object store.

        :param objects: Iterable over objects, should support __len__.
        :return: Pack object of the objects written.
        """
        if len(objects) == 0:
            # Don't bother writing an empty pack file
            return
        f, commit = self.add_pack()
        write_pack_data(f, objects, len(objects))
        return commit()


class DiskObjectStore(PackBasedObjectStore):
    """Git-style object store that exists on disk."""

    def __init__(self, path):
        """Open an object store.

        :param path: Path of the object store.
        """
        super(DiskObjectStore, self).__init__()
        self.path = path
        self.pack_dir = os.path.join(self.path, PACKDIR)
        self._pack_cache_time = 0

    def _load_packs(self):
        pack_files = []
        try:
            self._pack_cache_time = os.stat(self.pack_dir).st_mtime
            pack_dir_contents = os.listdir(self.pack_dir)
            for name in pack_dir_contents:
                # TODO: verify that idx exists first
                if name.startswith("pack-") and name.endswith(".pack"):
                    filename = os.path.join(self.pack_dir, name)
                    pack_files.append((os.stat(filename).st_mtime, filename))
        except OSError, e:
            if e.errno == errno.ENOENT:
                return []
            raise
        pack_files.sort(reverse=True)
        suffix_len = len(".pack")
        return [Pack(f[:-suffix_len]) for _, f in pack_files]

    def _pack_cache_stale(self):
        try:
            return os.stat(self.pack_dir).st_mtime > self._pack_cache_time
        except OSError, e:
            if e.errno == errno.ENOENT:
                return True
            raise

    def _get_shafile_path(self, sha):
        # Check from object dir
        return hex_to_filename(self.path, sha)

    def _iter_loose_objects(self):
        for base in os.listdir(self.path):
            if len(base) != 2:
                continue
            for rest in os.listdir(os.path.join(self.path, base)):
                yield base+rest

    def _get_loose_object(self, sha):
        path = self._get_shafile_path(sha)
        try:
            return ShaFile.from_path(path)
        except (OSError, IOError), e:
            if e.errno == errno.ENOENT:
                return None
            raise

    def _remove_loose_object(self, sha):
        os.remove(self._get_shafile_path(sha))

    def move_in_thin_pack(self, path):
        """Move a specific file containing a pack into the pack directory.

        :note: The file should be on the same file system as the
            packs directory.

        :param path: Path to the pack file.
        """
        data = ThinPackData(self.get_raw, path)

        # Write index for the thin pack (do we really need this?)
        temppath = os.path.join(self.pack_dir,
            sha_to_hex(urllib2.randombytes(20))+".tempidx")
        data.create_index_v2(temppath)
        p = Pack.from_objects(data, load_pack_index(temppath))

        # Write a full pack version
        temppath = os.path.join(self.pack_dir,
            sha_to_hex(urllib2.randombytes(20))+".temppack")
        write_pack(temppath, ((o, None) for o in p.iterobjects()), len(p))
        pack_sha = load_pack_index(temppath+".idx").objects_sha1()
        newbasename = os.path.join(self.pack_dir, "pack-%s" % pack_sha)
        os.rename(temppath+".pack", newbasename+".pack")
        os.rename(temppath+".idx", newbasename+".idx")
        final_pack = Pack(newbasename)
        self._add_known_pack(final_pack)
        return final_pack

    def move_in_pack(self, path):
        """Move a specific file containing a pack into the pack directory.

        :note: The file should be on the same file system as the
            packs directory.

        :param path: Path to the pack file.
        """
        p = PackData(path)
        entries = p.sorted_entries()
        basename = os.path.join(self.pack_dir,
            "pack-%s" % iter_sha1(entry[0] for entry in entries))
        f = GitFile(basename+".idx", "wb")
        try:
            write_pack_index_v2(f, entries, p.get_stored_checksum())
        finally:
            f.close()
        p.close()
        os.rename(path, basename + ".pack")
        final_pack = Pack(basename)
        self._add_known_pack(final_pack)
        return final_pack

    def add_thin_pack(self):
        """Add a new thin pack to this object store.

        Thin packs are packs that contain deltas with parents that exist
        in a different pack.
        """
        fd, path = tempfile.mkstemp(dir=self.pack_dir, suffix=".pack")
        f = os.fdopen(fd, 'wb')
        def commit():
            os.fsync(fd)
            f.close()
            if os.path.getsize(path) > 0:
                return self.move_in_thin_pack(path)
            else:
                return None
        return f, commit

    def add_pack(self):
        """Add a new pack to this object store.

        :return: Fileobject to write to and a commit function to
            call when the pack is finished.
        """
        fd, path = tempfile.mkstemp(dir=self.pack_dir, suffix=".pack")
        f = os.fdopen(fd, 'wb')
        def commit():
            os.fsync(fd)
            f.close()
            if os.path.getsize(path) > 0:
                return self.move_in_pack(path)
            else:
                return None
        return f, commit

    def add_object(self, obj):
        """Add a single object to this object store.

        :param obj: Object to add
        """
        dir = os.path.join(self.path, obj.id[:2])
        try:
            os.mkdir(dir)
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise
        path = os.path.join(dir, obj.id[2:])
        if os.path.exists(path):
            return # Already there, no need to write again
        f = GitFile(path, 'wb')
        try:
            f.write(obj.as_legacy_object())
        finally:
            f.close()

    @classmethod
    def init(cls, path):
        try:
            os.mkdir(path)
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise
        os.mkdir(os.path.join(path, "info"))
        os.mkdir(os.path.join(path, PACKDIR))
        return cls(path)


class MemoryObjectStore(BaseObjectStore):
    """Object store that keeps all objects in memory."""

    def __init__(self):
        super(MemoryObjectStore, self).__init__()
        self._data = {}

    def contains_loose(self, sha):
        """Check if a particular object is present by SHA1 and is loose."""
        return sha in self._data

    def contains_packed(self, sha):
        """Check if a particular object is present by SHA1 and is packed."""
        return False

    def __iter__(self):
        """Iterate over the SHAs that are present in this store."""
        return self._data.iterkeys()

    @property
    def packs(self):
        """List with pack objects."""
        return []

    def get_raw(self, name):
        """Obtain the raw text for an object.

        :param name: sha for the object.
        :return: tuple with numeric type and object contents.
        """
        return self[name].as_raw_string()

    def __getitem__(self, name):
        return self._data[name]

    def add_object(self, obj):
        """Add a single object to this object store.

        """
        self._data[obj.id] = obj

    def add_objects(self, objects):
        """Add a set of objects to this object store.

        :param objects: Iterable over a list of objects.
        """
        for obj, path in objects:
            self._data[obj.id] = obj


class ObjectImporter(object):
    """Interface for importing objects."""

    def __init__(self, count):
        """Create a new ObjectImporter.

        :param count: Number of objects that's going to be imported.
        """
        self.count = count

    def add_object(self, object):
        """Add an object."""
        raise NotImplementedError(self.add_object)

    def finish(self, object):
        """Finish the import and write objects to disk."""
        raise NotImplementedError(self.finish)


class ObjectIterator(object):
    """Interface for iterating over objects."""

    def iterobjects(self):
        raise NotImplementedError(self.iterobjects)


class ObjectStoreIterator(ObjectIterator):
    """ObjectIterator that works on top of an ObjectStore."""

    def __init__(self, store, sha_iter):
        """Create a new ObjectIterator.

        :param store: Object store to retrieve from
        :param sha_iter: Iterator over (sha, path) tuples
        """
        self.store = store
        self.sha_iter = sha_iter
        self._shas = []

    def __iter__(self):
        """Yield tuple with next object and path."""
        for sha, path in self.itershas():
            yield self.store[sha], path

    def iterobjects(self):
        """Iterate over just the objects."""
        for o, path in self:
            yield o

    def itershas(self):
        """Iterate over the SHAs."""
        for sha in self._shas:
            yield sha
        for sha in self.sha_iter:
            self._shas.append(sha)
            yield sha

    def __contains__(self, needle):
        """Check if an object is present.

        :note: This checks if the object is present in
            the underlying object store, not if it would
            be yielded by the iterator.

        :param needle: SHA1 of the object to check for
        """
        return needle in self.store

    def __getitem__(self, key):
        """Find an object by SHA1.

        :note: This retrieves the object from the underlying
            object store. It will also succeed if the object would
            not be returned by the iterator.
        """
        return self.store[key]

    def __len__(self):
        """Return the number of objects."""
        return len(list(self.itershas()))


def tree_lookup_path(lookup_obj, root_sha, path):
    """Lookup an object in a Git tree.

    :param lookup_obj: Callback for retrieving object by SHA1
    :param root_sha: SHA1 of the root tree
    :param path: Path to lookup
    """
    parts = path.split("/")
    sha = root_sha
    mode = None
    for p in parts:
        obj = lookup_obj(sha)
        if not isinstance(obj, Tree):
            raise NotTreeError(sha)
        if p == '':
            continue
        mode, sha = obj[p]
    return mode, sha


class MissingObjectFinder(object):
    """Find the objects missing from another object store.

    :param object_store: Object store containing at least all objects to be
        sent
    :param haves: SHA1s of commits not to send (already present in target)
    :param wants: SHA1s of commits to send
    :param progress: Optional function to report progress to.
    :param get_tagged: Function that returns a dict of pointed-to sha -> tag
        sha for including tags.
    :param tagged: dict of pointed-to sha -> tag sha for including tags
    """

    def __init__(self, object_store, haves, wants, progress=None,
                 get_tagged=None):
        haves = set(haves)
        self.sha_done = haves
        self.objects_to_send = set([(w, None, False) for w in wants
                                    if w not in haves])
        self.object_store = object_store
        if progress is None:
            self.progress = lambda x: None
        else:
            self.progress = progress
        self._tagged = get_tagged and get_tagged() or {}

    def add_todo(self, entries):
        self.objects_to_send.update([e for e in entries
                                     if not e[0] in self.sha_done])

    def parse_tree(self, tree):
        self.add_todo([(sha, name, not stat.S_ISDIR(mode))
                       for mode, name, sha in tree.entries()
                       if not S_ISGITLINK(mode)])

    def parse_commit(self, commit):
        self.add_todo([(commit.tree, "", False)])
        self.add_todo([(p, None, False) for p in commit.parents])

    def parse_tag(self, tag):
        self.add_todo([(tag.object[1], None, False)])

    def next(self):
        if not self.objects_to_send:
            return None
        (sha, name, leaf) = self.objects_to_send.pop()
        if not leaf:
            o = self.object_store[sha]
            if isinstance(o, Commit):
                self.parse_commit(o)
            elif isinstance(o, Tree):
                self.parse_tree(o)
            elif isinstance(o, Tag):
                self.parse_tag(o)
        if sha in self._tagged:
            self.add_todo([(self._tagged[sha], None, True)])
        self.sha_done.add(sha)
        self.progress("counting objects: %d\r" % len(self.sha_done))
        return (sha, name)


class ObjectStoreGraphWalker(object):
    """Graph walker that finds what commits are missing from an object store.

    :ivar heads: Revisions without descendants in the local repo
    :ivar get_parents: Function to retrieve parents in the local repo
    """

    def __init__(self, local_heads, get_parents):
        """Create a new instance.

        :param local_heads: Heads to start search with
        :param get_parents: Function for finding the parents of a SHA1.
        """
        self.heads = set(local_heads)
        self.get_parents = get_parents
        self.parents = {}

    def ack(self, sha):
        """Ack that a revision and its ancestors are present in the source."""
        ancestors = set([sha])

        # stop if we run out of heads to remove
        while self.heads:
            for a in ancestors:
                if a in self.heads:
                    self.heads.remove(a)

            # collect all ancestors
            new_ancestors = set()
            for a in ancestors:
                if a in self.parents:
                    new_ancestors.update(self.parents[a])

            # no more ancestors; stop
            if not new_ancestors:
                break

            ancestors = new_ancestors

    def next(self):
        """Iterate over ancestors of heads in the target."""
        if self.heads:
            ret = self.heads.pop()
            ps = self.get_parents(ret)
            self.parents[ret] = ps
            self.heads.update(ps)
            return ret
        return None
