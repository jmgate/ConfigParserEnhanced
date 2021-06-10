#!/bin/bash
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"

pushd $PWD

cd ${script_dir}
rm -rf deps > /dev/null 2>&1; mkdir deps; cd deps
git clone git@internal.gitlab.server:trilinos-devops-consolidation/code/ConfigParserEnhanced.git
git clone git@internal.gitlab.server:trilinos-devops-consolidation/code/SetEnvironment.git
git clone git@internal.gitlab.server:trilinos-devops-consolidation/code/DetermineSystem.git
git clone git@internal.gitlab.server:trilinos-devops-consolidation/code/KeywordParser.git
cd -

# snapshot dependencies in
ln -s deps/SetEnvironment/setenvironment/ .
ln -s deps/ConfigParserEnhanced/configparserenhanced/ .
ln -s deps/DetermineSystem/determinesystem/ .
ln -s deps/KeywordParser/keywordparser/ .

popd
