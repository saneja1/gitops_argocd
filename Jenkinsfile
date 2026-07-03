pipeline {
    agent any

    environment {
        DOCKERHUB_USERNAME = 'saneja1'
        IMAGE_NAME         = "${DOCKERHUB_USERNAME}/streamlit-app"
        IMAGE_TAG          = "${BUILD_NUMBER}"
        GITHUB_REPO        = 'https://github.com/saneja1/gitops_argocd.git'
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build Docker Image') {
            steps {
                dir('app') {
                    sh "docker build -t ${IMAGE_NAME}:${IMAGE_TAG} ."
                }
            }
        }

        stage('Push to DockerHub') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-credentials',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh "echo $DOCKER_PASS | docker login -u $DOCKER_USER --password-stdin"
                    sh "docker push ${IMAGE_NAME}:${IMAGE_TAG}"
                }
            }
        }

        stage('Update Image Tag in k8s Manifest') {
            steps {
                sh """
                    sed -i 's|image: ${IMAGE_NAME}:.*|image: ${IMAGE_NAME}:${IMAGE_TAG}|' k8s/deployment.yaml
                """
                sh "grep 'image:' k8s/deployment.yaml"
            }
        }

        stage('Commit and Push to GitHub') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'github-credentials',
                    usernameVariable: 'GIT_USER',
                    passwordVariable: 'GIT_TOKEN'
                )]) {
                    sh """
                        git config user.email "jenkins@ci.local"
                        git config user.name "Jenkins CI"
                        git add k8s/deployment.yaml
                        git commit -m "ci: update image tag to ${IMAGE_NAME}:${IMAGE_TAG} [skip ci]"
                        git push https://${GIT_USER}:${GIT_TOKEN}@github.com/saneja1/gitops_argocd.git HEAD:master
                    """
                }
            }
        }

        stage('AI Health Check') {
            steps {
                withCredentials([string(credentialsId: 'groq-api-key', variable: 'GROQ_API_KEY')]) {
                    sh "python3 scripts/health_check.py http://8.231.187.147:30095 ${GROQ_API_KEY} streamlit-app ${IMAGE_TAG}"
                }
            }
            post {
                failure {
                    withCredentials([usernamePassword(
                        credentialsId: 'github-credentials',
                        usernameVariable: 'GIT_USER',
                        passwordVariable: 'GIT_TOKEN'
                    )]) {
                        sh """
                            git revert HEAD --no-edit
                            git push https://${GIT_USER}:${GIT_TOKEN}@github.com/saneja1/gitops_argocd.git HEAD:master
                        """
                    }
                    echo "UNHEALTHY: Rolled back to previous image tag via git revert."
                }
            }
        }

    }

    post {
        success {
            echo "Build ${IMAGE_TAG} deployed and verified healthy by AI."
        }
        failure {
            echo "Pipeline failed."
        }
        always {
            sh "docker rmi ${IMAGE_NAME}:${IMAGE_TAG} || true"
        }
    }
}
