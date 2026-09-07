#!/usr/bin/env bash
# Read-only checks for the local smoke environment; never creates or deletes resources.
set -euo pipefail
context=k3d-laughtale-local
namespace=laughtale-smoke
kubectl --context "$context" wait node --all --for=condition=Ready --timeout=30s
kubectl --context "$context" -n "$namespace" rollout status deployment/smoke --timeout=30s
ready=$(kubectl --context "$context" -n "$namespace" get deployment smoke -o jsonpath='{.status.readyReplicas}')
test "$ready" = 2
kubectl --context "$context" -n "$namespace" get pods -o wide
curl --fail --silent --show-error --max-time 5 http://127.0.0.1/health
curl --fail --silent --show-error --max-time 5 http://127.0.0.1/ | head -n 1
kubectl --context "$context" top nodes
kubectl --context "$context" -n "$namespace" top pods
