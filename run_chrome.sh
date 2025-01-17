export HTTP_PROXY="http://127.0.0.1:8082"
export HTTPS_PROXY="http://127.0.0.1:8082"
google-chrome \
    --user-data-dir="$HOME/.config/google-chrome" \
    --profile-directory="Profile 10" \
    --disable-quic
