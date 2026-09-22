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
  Re-run `helm resolve-deps` after changing any subchart under `charts/`; the umbrella
  chart installs from packaged `.tgz` files in `charts/canvas-oda/charts/`, not live
  source paths.


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
`[charts/canvas-oda/values-openshift.yaml](../../charts/canvas-oda/values-openshift.yaml)`:
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
# CTK UC002-F005/F006 use odacompns-1 (same anyuid need as components for CTK images)
oc new-project odacompns-1 || true
oc adm policy add-scc-to-user anyuid -z default -n odacompns-1
oc adm policy add-scc-to-user anyuid -z deployer -n odacompns-1
cd feature-definition-and-test-kit
npm install
npm start
```

See [Executing-tests.md](../../feature-definition-and-test-kit/Executing-tests.md) for `.env`, utility `npm install`s, and tagged runs.


## Uninstall

```
helm uninstall ctk -n components
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

On CRC, ensure `mongo:*` resolves to `docker.io/library/mongo:*` in the cluster image registry (shortname mapping). Without that, `mongo` may resolve to an unreachable private registry and pods will sit in `ImagePullBackOff`.

### API gateway hostname

The API operator uses `api-operator-istio.configmap.publicHostname` for Istio
VirtualService `hosts` and for API URLs written to Component status. If unset,
VirtualServices default to `*` (routing still works), but on CRC there is no
ingress LoadBalancer hostname to discover — exposed APIs will not get usable
public URLs and clients that match on host (e.g. port-forward with
`Host: localhost`) need an explicit value.

Set it at install to the hostname you will use to reach the gateway — **not**
`host:port` (Istio rejects a port in the host field). For local access via
port-forward, use `localhost`; with an OpenShift Route, use the route hostname
(e.g. `components.apps-crc.testing`).

```
--set api-operator-istio.configmap.publicHostname=localhost
```

### Example: CRC install

```
helm install canvas charts/canvas-oda \
  -n canvas \
  -f charts/canvas-oda/values-openshift.yaml \
  --set preqrequisitechecks.istio=false \
  --set api-operator-istio.configmap.publicHostname=localhost \
  --timeout 600s
```

You can also save the `--set` lines in a local `values-crc.yaml`
and add `-f values-crc.yaml`, to save on typing.
