# This assumes you have /var/canvas symlinked to your repository.
# To enable these shortcuts run: echo ". /var/canvas/dotcanvasrc" >> ~/.bashrc
#
export PATH=~/Packages/phantomjs-1.5.0/bin:/usr/local/sbin:/usr/local/bin:/var/canvas/shell:$PATH
alias cdc="cd /var/canvas/website"
alias killsolr="kill -9 \$(ps aux|grep solr|awk '{ print \$2 }')"
alias ckill="killall -m nginx python redis-server java && killsolr"
alias dqkill="killall -m nginx python redis-server java"
alias runcanvas="clear && ckill; /var/canvas/website/local.py; ckill"
alias rundq="clear && dqkill; /var/canvas/website/local.py --project=drawquest; dqkill"
alias cclean="cdc; rm -f website/static/CACHE/*/*; find . | grep '\.pyc\$' | xargs rm"
alias shell="cdc && python manage.py shell"
alias dbshell="cdc && python manage.py dbshell"
alias gw='ssh -p 30583 -A ancientpsychictandemwarelephant.example.com'
alias jsapi="python manage.py generate_js_api"
alias dqjsapi="python manage.py generate_js_api --settings=settings_drawquest"
alias ctest="cpytest; cjstest"
alias iPhone='"/Applications/Xcode.app/Contents/Developer/Platforms/iPhoneSimulator.platform/Developer/Applications/iPhone Simulator.app/Contents/MacOS/iPhone Simulator"'
# GIT
alias gb="git branch"
alias gco="git checkout"
alias gci="git commit -am"
alias gsci="git commit -m"
alias gst="git status"
alias gsd="git diff --color --staged"
alias gpullr="git pull --rebase"
alias gpushr="gpullr && git push"
alias gl="git log"
alias gr="gl -10"
alias gsl="git stash list"
alias gss="git stash save"
alias gsp="git stash pop"
alias cronme="ssh \`ip -rg cron\`"

function gd {
    clear && git diff --color HEAD$1
}
function gdc {
    clear && git diff --color --cached HEAD$1
}
function gcip {
    gci "$1" && gpushr
}

alias a=ack
alias ackt="ack -G \"test.*\" --py"
alias m="python /var/canvas/website/manage.py"
alias dqm="DJANGO_SETTINGS_MODULE=settings_drawquest python /var/canvas/website/manage.py"

# --verbosity==0 to hide syncdb output.
function cpytest {
    cd /var/canvas/website
    BUILD_ID=dontKillMe ./nginx.py
    # If you change the excludes, please update them in jenkins_splitter.py as well.
    if hash xvfb-run 2>&-; then
        xvfb-run --server-args="-screen 0 1024x768x24" python manage.py test $@
    else
        python manage.py test $@
    fi
}

function dqpytest {
    echo "WARNING: only tests drawquest app for now."
    cd /var/canvas/website
    BUILD_ID=dontKillMe ./nginx.py --project=drawquest
    # If you change the excludes, please update them in jenkins_splitter.py as well.
    if hash xvfb-run 2>&-; then
        DJANGO_SETTINGS_MODULE=settings_drawquest xvfb-run --server-args="-screen 0 1024x768x24" python manage.py test drawquest $@
    else
        DJANGO_SETTINGS_MODULE=settings_drawquest python manage.py test drawquest $@ 
    fi
}

function cjstest {
    cd /var/canvas/website
    phantomjs tests/js/runner.js $@
    phantomjs tests/js/page_ready_check.js
}

function dqjstest {
    cd /var/canvas/website
    phantomjs tests/js/runner.js "http://dq.savnac.com" $@
    #TODO phantomjs tests/js/page_ready_check.js
}

function install_fixme_hook {
    ln -sf /var/canvas/shell/pre-commit /var/canvas/.git/hooks/pre-commit
}

install_fixme_hook

