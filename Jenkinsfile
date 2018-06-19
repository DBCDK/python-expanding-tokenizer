pipeline {
    agent { label "stretch" }
    triggers {
        pollSCM("H/3 * * * *")
    }
    options {
        buildDiscarder(logRotator(artifactDaysToKeepStr: "", artifactNumToKeepStr: "", daysToKeepStr: "30", numToKeepStr: "30"))
        timestamps()
    }
    stages {
        stage("build") {
            steps {
                script {
                    sh """
                        rm -rf dist deb_dist expanding?tokenizer*
                        python3 setup.py --no-user-cfg --command-packages=stdeb.command sdist_dsc --debian-version=${BUILD_NUMBER}kosmisk --verbose --copyright-file copyright.txt -z stable
                        (cd deb_dist/* && debuild -us -uc)
                    """
                }
            }
        }
        stage("upload") {
            steps {
                script {
                    if (env.BRANCH_NAME ==~ /master|trunk/) {
                        sh """
                            find .
                        	#cd deb_dist && \
                        	#for changes in *.changes; do \
                            #    rsync -av $RSYNC_SSH $changes `sed -e '1,/^Files:/d' -e '/^[A-Z]/,$d' -e 's/.* //' $changes` $RSYNC_TARGET; \
                            #done
                        """
                    }

                }
            }
        }
    }
}
