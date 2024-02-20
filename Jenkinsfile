// https://github.com/Rudd-O/shared-jenkins-libraries
@Library('shared-jenkins-libraries@master') _

def test_step() {
    return {
        sh "echo Test can only proceed in Qubes. >&2"
    }
}

genericFedoraRPMPipeline(null, null, null, null, test_step())
