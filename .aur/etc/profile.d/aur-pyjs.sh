#!/bin/bash
# add aur-pyjs to PATH; export APP_CONF

l=aur-pyjs; s=aur
if [ -z "$(type -t ${l} ${s})" ]; then
    for x in {,/aur,/usr,/usr/local,/opt,/opt/local}/etc/{${l}/${l},${s}/${s}}.conf; do
        if [ -f "${x}" ]; then
            export APP_CONF="${x}"
            [ "${x}" != "${x#/etc/}" ] || export PATH="${PATH}:${x%%/etc/*}/usr/bin"
            break
        fi
    done
fi
