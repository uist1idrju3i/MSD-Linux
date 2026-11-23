#!/bin/sh
# shellcheck disable=SC1091,SC2154
set -u
umask 077
export PATH=/sbin:/usr/sbin:/bin:/usr/bin
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
mount -t tmpfs tmpfs /run
mount -t tmpfs tmpfs /tmp
. /fixtures/settings
if [ -x /fixtures/strace ]; then /fixtures/strace -V; fi
run_client() {
    if [ -x /fixtures/strace ]; then
        /fixtures/strace -f -qq -s 256 -e trace=%file -o "$trace" "$@"
    else
        "$@"
    fi
}
export HOME=/root
mkdir -p /root/.ssh
chmod 700 /root/.ssh
modprobe cdc_ether
count=0
interface=
while [ -z "$interface" ]; do
    for path in /sys/class/net/*; do
        [ "${path##*/}" = lo ] || interface="${path##*/}"
    done
    [ -z "$interface" ] || break
    count=$((count + 1))
    [ "$count" -lt 30 ] || { echo SSH_FATAL_NETWORK; exit 1; }
    sleep 1
done
ip link set "$interface" up
ip addr add 10.0.2.15/24 dev "$interface"
ip route add default via 10.0.2.2
cp /fixtures/client /run/client
chmod 600 /run/client
if echo "$variants" | grep -qw dropbear; then
    /fixtures/dropbearconvert openssh dropbear /run/client /run/client.dropbear || exit 1
fi
if echo "$variants" | grep -qw putty; then
    /fixtures/puttygen /run/client -O private -o /run/client.ppk --new-passphrase /dev/null || exit 1
fi
cat /proc/mounts
for variant in $variants; do
    case "$variant" in
        openssh)
            ssh -V
            for kind in kex cipher mac key key-sig; do
                echo "SSH_ALGORITHMS openssh $kind"
                ssh -Q "$kind"
                echo SSH_ALGORITHMS_END
            done
            echo SSH_CONFIG_BEGIN
            ssh -G -F /dev/null example.invalid
            echo SSH_CONFIG_END
            ;;
        dropbear)
            dbclient -V
            dbclient -h
            for kind in kex cipher mac sig; do
                echo "SSH_ALGORITHMS dropbear $kind"
                dbclient -Q "$kind"
                echo SSH_ALGORITHMS_END
            done
            ;;
        putty) plink --version; plink --help ;;
    esac
    repeat=1
    while [ "$repeat" -le "$repetitions" ]; do
        for condition in good wrong; do
            cp "/fixtures/known-$condition" /root/.ssh/known_hosts
            before="$(sha256sum /root/.ssh/known_hosts)"
            echo "SSH_BEGIN $variant $condition $repeat"
            echo SSH_HOME_BEFORE
            find /root -type f -exec sha256sum '{}' ';'
            trace="/run/$variant-$condition-$repeat.trace"
            case "$variant" in
                openssh)
                    run_client ssh -vv -F /dev/null -o BatchMode=yes -o StrictHostKeyChecking=yes \
                        -o ConnectTimeout=10 \
                        -o UpdateHostKeys=no -o GlobalKnownHostsFile=/dev/null \
                        -o UserKnownHostsFile=/root/.ssh/known_hosts -o IdentitiesOnly=yes \
                        -i /run/client -p "$port" "$login@10.0.2.2" /bin/echo SSH_REMOTE_OK
                    code=$?
                    ;;
                dropbear)
                    run_client dbclient -T -o BatchMode=yes -o StrictHostKeyChecking=yes \
                        -i /run/client.dropbear -p "$port" \
                        "$login@10.0.2.2" /bin/echo SSH_REMOTE_OK </dev/null
                    code=$?
                    ;;
                putty)
                    fingerprint="$good_fingerprint"
                    [ "$condition" = good ] || fingerprint="$wrong_fingerprint"
                    run_client plink -v -batch -ssh -noagent -i /run/client.ppk \
                        -hostkey "$fingerprint" -P "$port" "$login@10.0.2.2" /bin/echo SSH_REMOTE_OK
                    code=$?
                    ;;
            esac
            after="$(sha256sum /root/.ssh/known_hosts)"
            echo SSH_HOME_AFTER
            find /root -type f -exec sha256sum '{}' ';'
            if [ -f "$trace" ]; then
                echo SSH_TRACE_BEGIN
                cat "$trace"
                echo SSH_TRACE_END
            fi
            changed=0
            [ "$before" = "$after" ] || changed=1
            echo "SSH_RESULT $variant $condition $repeat $code $changed"
        done
        repeat=$((repeat + 1))
    done
done
echo SSH_COMPARE_DONE
while :; do sleep 1; done
