import requests


class Keycloak:

    def __init__(self, url):
        self._url = url

    def _request_token(self, token_realm: str, data: dict) -> str:
        """POST to the token endpoint and return access_token."""
        token_url = (
            f"{self._url}/realms/{token_realm}/protocol/openid-connect/token"
        )
        try:
            r = requests.post(token_url, data=data)
            r.raise_for_status()
            return r.json()["access_token"]
        except requests.HTTPError as e:
            raise RuntimeError(
                f"token request failed with HTTP status {r.status_code}: {e}"
            ) from None

    def get_token(
        self,
        auth_type: str,
        user: str,
        pwd: str,
        token_realm: str = "master",
    ) -> str:
        """
        Obtain an Admin API token using the configured auth mode.

        ``auth_type``:
          - ``password`` (default): ``user`` / ``pwd`` as admin username/password
            via ``admin-cli``
          - ``clientCredentials``: ``user`` / ``pwd`` as client id / secret

        ``token_realm`` is the realm that issues the token (almost always
        ``master``). It is independent of the Canvas component realm
        (e.g. ``odari``).
        """
        normalized = (auth_type or "password").replace("_", "").replace("-", "").lower()
        if normalized in ("clientcredentials", "serviceaccount"):
            data = {
                "grant_type": "client_credentials",
                "client_id": user,
                "client_secret": pwd,
            }
        else:
            data = {
                "username": user,
                "password": pwd,
                "grant_type": "password",
                "client_id": "admin-cli",
            }
        return self._request_token(token_realm, data)

    def create_client(self, client: str, url: str, token: str, realm: str) -> None:
        """
        POSTs a new client named according to the componentName for
        a new component

        Returns nothing, or raises an exception for the caller to catch
        """
        if url == "":
            json_obj = {"clientId": client, "serviceAccountsEnabled": True}
        else:
            json_obj = {"clientId": client, "rootUrl": url, "serviceAccountsEnabled": True}

        try:  # to create the client in Keycloak
            r = requests.post(
                self._url + "/admin/realms/" + realm + "/clients",
                json=json_obj,
                headers={"Authorization": "Bearer " + token},
            )
            r.raise_for_status()
        except requests.HTTPError as e:
            # ! This might hide actual errors
            # ! The keycloak API isn't idempotent.
            # ! If a client exists it returns 409 instead of 201
            # ! But why did we call create_client for a client that
            # ! exists?
            if r.status_code == 409:
                pass  # because the client exists, which is what we want
            else:
                raise RuntimeError(
                    "create_client failed with HTTP status " f"{r.status_code}: {e}"
                ) from None

    def del_client(self, client: str, token: str, realm: str) -> None:
        """
        DELETEs a client

        Returns nothing, or raises an exception for the caller to catch
        """

        try:  # to GET the id of the existing client that we need to DELETE it
            r_a = requests.get(
                self._url + "/admin/realms/" + realm + "/clients",
                params={"clientId": client},
                headers={"Authorization": "Bearer " + token},
            )
            r_a.raise_for_status()
        except requests.HTTPError as e:
            raise RuntimeError(
                "del_client failed to get client ID with HTTP status "
                f"{r_a.status_code}: {e}"
            ) from None

        if len(r_a.json()) > 0:  # we found a client with a matching name
            target_client_id = r_a.json()[0]["id"]

            try:  # to delete the client matching the id we found
                r_b = requests.delete(
                    self._url
                    + "/admin/realms/"
                    + realm
                    + "/clients/"
                    + target_client_id,
                    headers={"Authorization": "Bearer " + token},
                )
                r_b.raise_for_status()
            except requests.HTTPError as e:
                raise RuntimeError(
                    "del_client failed to delete client with HTTP status "
                    f"{r_b.status_code}: {e}"
                ) from None

        else:  # we didn't find a client with a matching name
            # ! This might hide actual errors
            # ! If the client doesn't exist the API call returns an
            # ! empty JSON array, but why did we call del_client for a
            # ! client that didn't exist?
            pass  # because the client doesn't exist, which is OK

    def get_client_list(self, token: str, realm: str) -> dict:
        """
        GETs a list of clients in the realm to ensure there is a
        client to match the componentName

        Returns a dictonary of clients and ids or raises
        an exception for the caller to catch
        """
        try:
            r = requests.get(
                self._url + "/admin/realms/" + realm + "/clients",
                headers={"Authorization": "Bearer " + token},
            )
            r.raise_for_status()
            client_list = dict((d["clientId"], d["id"]) for d in r.json())
            return client_list
        except requests.HTTPError as e:
            raise RuntimeError(
                "get_client_list failed with HTTP status " f"{r.status_code}: {e}"
            ) from None

    def add_role(self, role: str, client_id: str, token: str, realm: str, description: str = None) -> None:
        """
        POST new roles to the right client in the right realm in
        Keycloak

        Returns nothing or raises an exception for the caller to catch
        """

        # Build the JSON payload with role name and optional description
        role_data = {"name": role}
        if description is not None:
            role_data["description"] = description

        try:  # to add new role to Keycloak
            r = requests.post(
                self._url
                + "/admin/realms/"
                + realm
                + "/clients/"
                + client_id
                + "/roles",
                json=role_data,
                headers={"Authorization": "Bearer " + token},
            )
            r.raise_for_status()
        except requests.HTTPError as e:
            if r.status_code == 409:
                pass  # because the role already exists, which is acceptable but suspicious
            else:
                raise RuntimeError(
                    "add_role failed with HTTP status " f"{r.status_code}: {e}"
                ) from None

    def del_role(self, role: str, client: str, token: str, realm: str) -> None:
        """
        DELETE removed roles from the right client in the right realm
        in Keycloak

        Returns nothing or raises an exception for the caller to catch
        """

        try:  # to remove role from Keycloak
            r = requests.delete(
                self._url
                + "/admin/realms/"
                + realm
                + "/clients/"
                + client
                + "/roles/"
                + role,
                headers={"Authorization": "Bearer " + token},
            )
            r.raise_for_status()
        except requests.HTTPError as e:
            if r.status_code == 404:
                pass  # because the role does not exist which is acceptable but suspicious
            else:
                raise RuntimeError(
                    "del_role failed with HTTP status " f"{r.status_code}: {e}"
                ) from None