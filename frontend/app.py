def login_user(username, password):
    try:
        response = api_request(
            "POST",
            "/auth/login",
            json={"username": username, "password": password},
        )

        if not response.ok:
            try:
                error_data = response.json()
                detail = error_data.get("detail", response.text[:300])
            except ValueError:
                detail = response.text[:300]

            return False, f"Login API error (HTTP {response.status_code}): {detail}"

        token = response.json().get("access_token")

        if not token:
            return False, "Authentication token was not returned."

        profile = api_request("GET", "/auth/me", token)

        if not profile.ok:
            return False, f"Profile API error (HTTP {profile.status_code})."

        st.session_state.token = token
        st.session_state.user = profile.json()

        return True, "Login successful."

    except requests.RequestException as exc:
        return False, f"Connection error: {type(exc).__name__}"