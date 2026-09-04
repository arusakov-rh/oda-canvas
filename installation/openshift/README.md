# ODA Canvas on OpenShift

Tested on OpenShift 4.x with OSSM 3 (Istio Sail operator). CRC-specific notes are in [§ CodeReady Containers (CRC)](#codeready-containers-crc) below.

## Prerequisites

- `oc login` to the cluster with `cluster-admin`
- Helm 3.x installed; add repos and install resolver plugin:
  ```
  helm repo add hashicorp https://helm.releases.hashicorp.com
  helm repo add bitnami https://charts.bitnami.com/bitnami
  helm repo add jetstack https://charts.jetstack.io
  helm repo add kong https://charts.konghq.com       # needed by resolve-deps even if not installed
  helm repo add apisix https://charts.apiseven.com   # same
  helm repo update
  helm plugin install --version "main" https://github.com/Noksa/helm-resolve-deps.git
  ```
- Clone the repo and resolve chart dependencies:
  ```
  cd charts/canvas-oda
  helm resolve-deps
  cd ../..
  ```


## 1. Install Operators

- cert-manager
- Red Hat OpenShift Service Mesh 3 (Istio Sail)


## 2. Setup Istio control plane and ingress gateway

Create the Istio control plane:

```
oc create namespace istio-system
oc create namespace istio-cni

oc apply -f - <<'EOF'
apiVersion: sailoperator.io/v1
kind: IstioCNI
metadata:
  name: default
  namespace: istio-cni
spec:
  version: v1.24.3
  namespace: istio-cni
EOF

oc apply -f - <<'EOF'
apiVersion: sailoperator.io/v1
kind: Istio
metadata:
  name: default
  namespace: istio-system
spec:
  version: v1.24.3
  namespace: istio-system
EOF
```

Create the ingress gateway:

```
oc create namespace istio-ingress
oc label namespace istio-ingress istio-injection=enabled
```

Wait until `oc get istio default -n istio-system` shows `Healthy`.


## 3. Pre-install SCCs

```
oc new-project canvas
oc adm policy add-scc-to-user nonroot-v2 -z default -n canvas
oc adm policy add-scc-to-user nonroot-v2 -z canvas-keycloak -n canvas
```


## 4. Install Canvas

OpenShift chart overrides are in
[`charts/canvas-oda/values-openshift.yaml`](../../charts/canvas-oda/values-openshift.yaml):
bundled cert-manager off, Vault RH UBI image, `global.openshift`, etc.

```
helm install canvas charts/canvas-oda \
  -n canvas \
  -f charts/canvas-oda/values-openshift.yaml \
  --timeout 600s
```

See [installation/README.md](../README.md#5-reference-implementation) for why `--wait` should not be used on Canvas installs.


## 5. Running the CTK

```
oc new-project components || true
oc adm policy add-scc-to-user anyuid -z default -n components
oc adm policy add-scc-to-user anyuid -z deployer -n components
cd feature-definition-and-test-kit
npm install
npm start
```


## Uninstall

```
helm uninstall canvas -n canvas
oc delete pvc -n canvas --all
oc delete pvc -n canvas-vault --all
oc delete ns canvas canvas-vault components
```


## CodeReady Containers (CRC)

CRC is a useful dev target but has two quirks that do not apply to a typical
managed OCP cluster. The local overrides below can/should be used when deploying on CRC.

### Istio pre-install check

The chart's `preqrequisitechecks.istio` hook expects `istio-ingress` to be a
`LoadBalancer` with an external IP. CRC has no cloud LB provider, so the hook
fails even when Istio is healthy.

Disable the check at install time:

```
--set preqrequisitechecks.istio=false
```

Or uncomment the block in `values-openshift.yaml` (marked CRC-only there).

### MongoDB image pull

As of this writing, `mongo` shortname resolves to a JFrog repo that is no more available for general public. A full OCP cluster is expected to have a more up-to-date mapping and to resolve `mongo` to another repo that has the image in public access (or at least in Red Hat registries).

If `canvas-svcinv-mongodb` is in `ImagePullBackOff`, override explicitly:

```
--set canvas-info-service.mongodb.image=docker.io/library/mongo:6.0
```

### Example: CRC install

```
helm install canvas charts/canvas-oda \
  -n canvas \
  -f charts/canvas-oda/values-openshift.yaml \
  --set preqrequisitechecks.istio=false \
  --set canvas-info-service.mongodb.image=docker.io/library/mongo:6.0 \
  --timeout 600s
```

You can also save the two `--set` lines in a local `values-crc.yaml`
and add `-f values-crc.yaml`, to save on typing.
