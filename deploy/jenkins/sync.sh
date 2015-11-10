#!/bin/bash
set -ex
JENKINS_CANVAS="/var/canvas/deploy/jenkins"
JENKINS_LIB="/var/lib/jenkins"
cd $JENKINS_CANVAS
for JOB in `ls $JENKINS_LIB/jobs`; do
  mkdir -p $JENKINS_CANVAS/jobs/$JOB
  cp $JENKINS_LIB/jobs/$JOB/config.xml $JENKINS_CANVAS/jobs/$JOB
  git add jobs/$JOB
done
cp $JENKINS_LIB/config.xml $JENKINS_CANVAS
cp $JENKINS_LIB/plugins/*.hpi $JENKINS_CANVAS/plugins
git add config.xml plugins
git status
echo -e "\n==> ALL SET! git commit -am and push."
