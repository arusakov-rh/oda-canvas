## Preparation
- `oc login ...`
- Setup helm
  - Install helm
  - Do https://github.com/tmforum-oda/oda-canvas/blob/master/installation/README.md#2-helm

## Install Red Hat Service Mesh
- Install the Service Mesh operator as per https://access.redhat.com/documentation/en-us/openshift_container_platform/4.15/html/service_mesh/service-mesh-2-x#installing-ossm
- `oc create namespace istio-system`
- Create ServiceMeshControlPlane in istio-system
  - `Name: istio-cp`
  - `Version: v2.4` # Shouldn't really matter?
  - `Mode: ClusterWide` # TODO: MultiTenant
- No need to create ServiceMeshMember(Roll) as the default ClusterWide SMCP configuration automatically adds projects labeled with istio-injection=enabled, and this is exactly the label that the Canvas chart uses

## ODA Canvas installation
- `oc new-project canvas`
- `oc adm policy add-scc-to-user nonroot-v2 -z default`
- `oc adm policy add-scc-to-user nonroot-v2 -z canvas-keycloak` # If using non-RH keycloak
- `helm install -f charts/canvas-oda/values.yaml canvas oda-canvas/canvas-oda`

## Add ingress for keycloak
```yaml
spec:
  rules:
    - host: canvas-keycloak.apps-crc.testing # Change as necessary
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: canvas-keycloak
                port:
                  number: 8083
```

## Patch RBAC
- Apply [rbac.yaml.diff](./rbac.yaml.diff) to resources defined by charts/controller/templates/rbac.yaml

## Running the CTK
- `cd ../../feature-definition-and-test-kit`
- `oc project components`
- `oc adm policy add-scc-to-user anyuid -z default -z deployer`
- Proceed as per https://github.com/tmforum-oda/oda-canvas/blob/master/feature-definition-and-test-kit/Executing-tests.md - should be 75% pass as of this writing
