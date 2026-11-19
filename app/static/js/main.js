
/* =========================================================
   VOTESPHERE — SHARED FRONTEND JAVASCRIPT
   ========================================================= */

document.addEventListener("DOMContentLoaded", () => {

    // ---------- Bootstrap Tooltips ----------
    const tooltipElements = document.querySelectorAll(
        '[data-bs-toggle="tooltip"]'
    );

    if (typeof bootstrap !== "undefined") {
        tooltipElements.forEach((element) => {
            new bootstrap.Tooltip(element);
        });
    }


    // ---------- Bootstrap Popovers ----------
    const popoverElements = document.querySelectorAll(
        '[data-bs-toggle="popover"]'
    );

    if (typeof bootstrap !== "undefined") {
        popoverElements.forEach((element) => {
            new bootstrap.Popover(element);
        });
    }


    // ---------- Auto-dismiss Flash Messages ----------
    const flashMessages = document.querySelectorAll(
        "#flashContainer .alert"
    );

    flashMessages.forEach((message) => {
        setTimeout(() => {
            if (typeof bootstrap !== "undefined") {
                const alertInstance =
                    bootstrap.Alert.getOrCreateInstance(message);

                alertInstance.close();
            } else {
                message.remove();
            }
        }, 5000);
    });


    // ---------- Form Validation ----------
    const forms = document.querySelectorAll(".needs-validation");

    forms.forEach((form) => {
        form.addEventListener("submit", (event) => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }

            form.classList.add("was-validated");
        });
    });


    // ---------- Password Visibility Toggle ----------
    // Supports both data-toggle-password and data-password-toggle.
    const passwordToggles = document.querySelectorAll(
        "[data-toggle-password], [data-password-toggle]"
    );

    passwordToggles.forEach((toggle) => {
        toggle.addEventListener("click", () => {
            const targetId =
                toggle.dataset.togglePassword ||
                toggle.dataset.passwordToggle;

            const passwordInput =
                document.getElementById(targetId);

            if (!passwordInput) {
                return;
            }

            const isPassword =
                passwordInput.type === "password";

            passwordInput.type =
                isPassword ? "text" : "password";

            const icon = toggle.querySelector("i");

            if (icon) {
                icon.classList.toggle("bi-eye", !isPassword);
                icon.classList.toggle("bi-eye-slash", isPassword);
            }

            toggle.setAttribute(
                "aria-label",
                isPassword ? "Hide password" : "Show password"
            );
        });
    });


    // ---------- Confirm Dangerous Actions ----------
    const confirmButtons = document.querySelectorAll(
        "[data-confirm]"
    );

    confirmButtons.forEach((button) => {
        button.addEventListener("click", (event) => {
            const message =
                button.dataset.confirm ||
                "Are you sure you want to continue?";

            if (!window.confirm(message)) {
                event.preventDefault();
            }
        });
    });


    // ---------- Loading State for Forms ----------
    const loadingForms = document.querySelectorAll(
        "[data-loading-form]"
    );

    loadingForms.forEach((form) => {
        form.addEventListener("submit", () => {
            if (!form.checkValidity()) {
                return;
            }

            const submitButton = form.querySelector(
                'button[type="submit"]'
            );

            if (!submitButton) {
                return;
            }

            if (submitButton.dataset.loading === "true") {
                return;
            }

            submitButton.dataset.loading = "true";
            submitButton.disabled = true;

            const originalText = submitButton.innerHTML;

            submitButton.dataset.originalText = originalText;

            submitButton.innerHTML = `
                <span
                    class="spinner-border spinner-border-sm"
                    role="status"
                    aria-hidden="true"
                ></span>
                Please wait...
            `;
        });
    });


    // ---------- Current Year ----------
    const yearElements = document.querySelectorAll(
        "[data-current-year]"
    );

    yearElements.forEach((element) => {
        element.textContent = new Date().getFullYear();
    });


    // ---------- Active Sidebar Link ----------
    const currentPath = window.location.pathname;

    const sidebarLinks = document.querySelectorAll(
        ".sidebar-link"
    );

    sidebarLinks.forEach((link) => {
        try {
            const linkPath = new URL(
                link.href,
                window.location.origin
            ).pathname;

            if (
                linkPath === currentPath &&
                currentPath !== "/"
            ) {
                link.classList.add("active");
            }
        } catch (error) {
            console.warn("Invalid sidebar link:", link.href);
        }
    });

});


/* =========================================================
   SHARED API HELPER
   ========================================================= */

/**
 * Sends requests to the Flask API.
 *
 * Example:
 *
 * apiRequest("/login", {
 *     method: "POST",
 *     body: {
 *         email: "user@example.com",
 *         password: "password"
 *     }
 * });
 */

async function apiRequest(url, options = {}) {

    const config = {
        method: options.method || "GET",

        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {})
        },

        credentials: "same-origin"
    };

    if (options.body !== undefined) {
        config.body = JSON.stringify(options.body);
    }

    try {
        const response = await fetch(url, config);

        const contentType =
            response.headers.get("content-type") || "";

        let data = {};

        if (contentType.includes("application/json")) {
            data = await response.json();
        } else {
            data = {
                message: await response.text()
            };
        }

        if (!response.ok) {
            const errorMessage =
                data.error ||
                data.message ||
                "Something went wrong.";

            throw new Error(errorMessage);
        }

        return data;

    } catch (error) {
        console.error("API Request Error:", error);
        throw error;
    }

}


/* =========================================================
   SHARED UI HELPERS
   ========================================================= */


/**
 * Displays a temporary notification.
 *
 * Usage:
 * showToast("Vote recorded successfully!", "success");
 */

function showToast(message, type = "info") {

    const container = document.getElementById("toastContainer");

    if (!container) {
        console.warn("Toast container not found.");
        return;
    }

    const toast = document.createElement("div");

    toast.className = `alert alert-${type} shadow-sm`;
    toast.setAttribute("role", "alert");

    // textContent prevents HTML injection from message strings.
    toast.textContent = message;

    container.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 4000);

}


/**
 * Formats a date for display.
 *
 * Example:
 * formatDate("2026-11-01T09:00:00")
 */

function formatDate(dateValue) {

    if (!dateValue) {
        return "Not specified";
    }

    const date = new Date(dateValue);

    if (Number.isNaN(date.getTime())) {
        return "Invalid date";
    }

    return date.toLocaleString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit"
    });

}


/**
 * Formats a number with Indian number grouping.
 */

function formatNumber(value) {

    const number = Number(value);

    if (!Number.isFinite(number)) {
        return "0";
    }

    return number.toLocaleString("en-IN");

}


/* =========================================================
   VOTESPHERE AUTHENTICATION
   ========================================================= */


/**
 * Displays an authentication message.
 */

function displayAuthMessage(element, message, type = "error") {

    if (!element) {
        return;
    }

    element.textContent = message;
    element.className = `auth-message ${type}`;

}


/**
 * Resets the submit button.
 */

function resetAuthButton(button, originalHTML) {

    if (!button) {
        return;
    }

    button.disabled = false;
    button.innerHTML = originalHTML;

}


/* ---------- Registration Form ---------- */

const registerForm = document.getElementById("registerForm");

if (registerForm) {

    registerForm.addEventListener("submit", async (event) => {

        event.preventDefault();

        const name =
            document.getElementById("name").value.trim();

        const email =
            document.getElementById("email").value.trim();

        const password =
            document.getElementById("password").value;

        const confirmPassword =
            document.getElementById("confirmPassword").value;

        const message =
            document.getElementById("registerMessage");

        const submitButton =
            registerForm.querySelector(".auth-submit");

        const originalHTML =
            submitButton.innerHTML;


        // Clear previous messages.
        displayAuthMessage(message, "");


        // Validate required fields.
        if (!name || !email || !password || !confirmPassword) {

            displayAuthMessage(
                message,
                "Please fill in all required fields."
            );

            return;
        }


        // Validate password confirmation.
        if (password !== confirmPassword) {

            displayAuthMessage(
                message,
                "Passwords do not match."
            );

            return;
        }


        // Validate password length.
        if (password.length < 8) {

            displayAuthMessage(
                message,
                "Password must be at least 8 characters."
            );

            return;
        }


        submitButton.disabled = true;
        submitButton.innerHTML = `
            <span
                class="spinner-border spinner-border-sm"
                role="status"
                aria-hidden="true"
            ></span>
            Creating account...
        `;


        try {

            await apiRequest("/register", {
                method: "POST",

                body: {
                    name,
                    email,
                    password
                }
            });


            displayAuthMessage(
                message,
                "Account created successfully! Redirecting to login...",
                "success"
            );


            // Redirect after successful registration.
            setTimeout(() => {
                window.location.href = "/login";
            }, 1200);


        } catch (error) {

            displayAuthMessage(
                message,
                error.message ||
                "Unable to create account. Please try again."
            );

            resetAuthButton(
                submitButton,
                originalHTML
            );

        }

    });

}


/* ---------- Login Form ---------- */

const loginForm = document.getElementById("loginForm");

if (loginForm) {

    loginForm.addEventListener("submit", async (event) => {

        event.preventDefault();

        const email =
            document.getElementById("email").value.trim();

        const password =
            document.getElementById("password").value;

        const message =
            document.getElementById("loginMessage");

        const submitButton =
            loginForm.querySelector(".auth-submit");

        const originalHTML =
            submitButton.innerHTML;


        // Clear previous messages.
        displayAuthMessage(message, "");


        // Validate required fields.
        if (!email || !password) {

            displayAuthMessage(
                message,
                "Please enter your email and password."
            );

            return;
        }


        submitButton.disabled = true;
        submitButton.innerHTML = `
            <span
                class="spinner-border spinner-border-sm"
                role="status"
                aria-hidden="true"
            ></span>
            Signing in...
        `;


        try {

            await apiRequest("/login", {
                method: "POST",

                body: {
                    email,
                    password
                }
            });


            // Redirect after successful login.
            window.location.href = "/dashboard";


        } catch (error) {

            displayAuthMessage(
                message,
                error.message ||
                "Invalid email or password."
            );

            resetAuthButton(
                submitButton,
                originalHTML
            );

        }

    });

}
