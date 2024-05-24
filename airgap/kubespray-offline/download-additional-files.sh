FILES_DIR=outputs/files

decide_relative_dir() {
    local url=$1
    local rdir
    rdir=$url
    rdir=$(echo $rdir | sed 's@.*/releases/download/\(v[0-9.]*\)/.*@\1@')
    if [ "$url" != "$rdir" ]; then
        echo $rdir
        return
    fi
}

get_url() {
    url=$1
    filename="${url##*/}"

    rdir=$(decide_relative_dir $url)

    if [ -n "$rdir" ]; then
        if [ ! -d $FILES_DIR/$rdir ]; then
            mkdir -p $FILES_DIR/$rdir
        fi
    else
        rdir="."
    fi

    if [ ! -e $FILES_DIR/$rdir/$filename ]; then
        echo "==> Download $url"
        for i in {1..3}; do
            curl --location --show-error --fail --output $FILES_DIR/$rdir/$filename $url && return
            echo "curl failed. Attempt=$i"
        done
        echo "Download failed, exit : $url"
        exit 1
    else
        echo "==> Skip $url"
    fi
}

#get_url() {
#    url=$1
#    filename="${url##*/}"
#
#    echo "==> Download $url"
#    for i in {1..3}; do
#        curl --location --show-error --fail --output $FILES_DIR/$filename $url && return
#        echo "curl failed. Attempt=$i"
#    done
#    echo "Download failed, exit : $url"
#    exit 1
#}

get_url https://github.com/xiilab/uyuni-login-theme/releases/download/v1.1.4/keycloak-theme.jar
