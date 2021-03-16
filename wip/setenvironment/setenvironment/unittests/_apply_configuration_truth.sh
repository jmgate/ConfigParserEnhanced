        #!/usr/bin/env bash

        # envvar_append_or_create
        #  $1 = envvar name
        #  $2 = string to append
        function envvar_append_or_create() {
            if [[ ! -n "${!1+1}" ]]; then
                export ${1}="${2}"
            else
                export ${1}="${!1}:${2}"
            fi
        }

        # envvar_prepend_or_create
        #  $1 = envvar name
        #  $2 = string to prepend
        function envvar_prepend_or_create() {
            if [[ ! -n "${!1+1}" ]]; then
                export ${1}="${2}"
            else
                export ${1}="${2}:${!1}"
            fi
        }

        # envvar_set_or_create
        #  $1 = envvar name
        #  $2 = string to prepend
        function envvar_set_or_create() {
            export ${1:?}="${2:?}"
        }

        # envvar_remove_substr
        # $1 = envvar name
        # $2 = substring to remove
        function envvar_remove_substr() {
            local envvar=${1:?}
            local substr=${2:?}
            #echo "envvar   : ${envvar}" > /dev/stdout
            #echo "to_remove: ${substr}" > /dev/stdout
            if [[ "${substr}" == *"#"* ]]; then
                printf "%s
" "ERROR: $FUNCNAME: "$substr" contains a '#' which is invalid." 2>&1
                return
            fi
            if [ ! -z ${1:?} ]; then
                export ${envvar}=$(echo ${!envvar} | sed s#${substr}##g)
            fi
        }

        # envvar_remove_path_entry
        # $1 = A path style envvar name
        # $2 = Entry to remove from the path.
        function envvar_remove_path_entry() {
            local envvar=${1:?}
            local to_remove=${2:?}
            local new_value=${!envvar}
            #echo -e "envvar = ${envvar}" > /dev/stdout
            #echo -e "to_remove = ${to_remove}" > /dev/stdout
            #echo -e "new_value = ${new_value}" > /dev/stdout
            if [ ! -z ${envvar} ]; then
                new_value=:${new_value}:
                new_value=${new_value//:${to_remove}:/:}
                new_value=${new_value#:1}
                new_value=${new_value%:1}
                export ${envvar}=${new_value}
            fi
        }

        # envvar_op
        # $1 = operation    (set, append, prepend, unset)
        # $2 = arg1         (envvar name)
        # $3 = arg2         (envvar value - optional)
        function envvar_op() {
            local op=${1:?}
            local arg1=${2:?}
            local arg2=${3}
            if [[ "${op:?}" == "set" ]]; then
                envvar_set_or_create ${arg1:?} ${arg2:?}
            elif [[ "${op:?}" == "unset" ]]; then
                unset ${arg1:?}
            elif [[ "${op:?}" == "append" ]]; then
                envvar_append_or_create ${arg1:?} ${arg2:?}
            elif [[ "${op:?}" == "prepend" ]]; then
                envvar_prepend_or_create ${arg1:?} ${arg2:?}
            elif [[ "${op:?}" == "remove_substr" ]]; then
                envvar_remove_substr ${arg1:?} ${arg2:?}
            else
                echo -e "!! ERROR (BASH): Unknown operation: ${op:?}"
            fi
        }

# -------------------------------------------------
#   S E T E N V I R O N M E N T   C O M M A N D S
# -------------------------------------------------
envvar_op set FOO bar
envvar_op append FOO baz
envvar_op prepend FOO foo
envvar_op set BAR foo
envvar_op remove_substr FOO bar
envvar_op unset FOO
module purge
module use setenvironment/unittests/modulefiles
module load gcc/4.8.4
module load boost/1.10.1
module load gcc/4.8.4
module unload boost
module swap gcc gcc/7.3.0


