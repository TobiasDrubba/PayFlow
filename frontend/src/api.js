const API_URL =
  (window._env_ && window._env_.REACT_APP_API_URL) ||
  process.env.REACT_APP_API_URL;
if (!API_URL) {
  throw new Error("REACT_APP_API_URL environment variable is not set");
}

// Helper to decode JWT and check expiration
function isTokenValid(token) {
  if (!token) return false;
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    console.log(payload.exp * 1000 > Date.now())
    if (!payload.exp) return false;
    return payload.exp * 1000 > Date.now();
  } catch {
    return false;
  }
}

function ensureValidToken() {
  const token = localStorage.getItem("token");
  if (!token || !isTokenValid(token)) {
    localStorage.removeItem("token");
    return false;
  }
  return true;
}

// Centralized fetch helper
async function fetchWithAuth(url, { method = "GET", headers = {}, body, isForm = false } = {}) {
  if (!ensureValidToken()) {
      window.location.reload();
      return;
  }
  const token = localStorage.getItem("token");
  const authHeader = token ? { Authorization: `Bearer ${token}` } : {};
  let finalHeaders = { ...headers, ...authHeader };
  if (!isForm && body && !(body instanceof FormData)) {
    finalHeaders["Content-Type"] = "application/json";
    body = JSON.stringify(body);
  }
  const response = await fetch(url, {
    method,
    headers: finalHeaders,
    body,
  });
  if (!response.ok) {
    let err = {};
    try { err = await response.json(); } catch {}
    throw new Error(err.detail || "Request failed");
  }
  return response;
}

export async function fetchPayments() {
  const response = await fetchWithAuth(`${API_URL}/payments`);
  return response.json();
}

export async function fetchCategories() {
  const response = await fetchWithAuth(`${API_URL}/payments/categories`);
  return response.json();
}

export async function updatePaymentCategory(paymentId, custCategory, allForMerchant = false) {
  const response = await fetchWithAuth(
    `${API_URL}/payments/${paymentId}/category`,
    {
      method: "PATCH",
      body: { cust_category: custCategory, all_for_merchant: allForMerchant },
    }
  );
  return response.json();
}

export async function fetchCategoryTree() {
  const response = await fetchWithAuth(`${API_URL}/payments/categories/tree`);
  return response.json();
}

export async function updateCategoryTree(tree) {
  const response = await fetchWithAuth(
    `${API_URL}/payments/categories/tree`,
    { method: "PUT", body: { tree } }
  );
  return response.json();
}

export async function fetchAggregation({ start_date, end_date } = {}) {
  const body = {};
  if (start_date) body.start_date = start_date;
  if (end_date) body.end_date = end_date;
  const response = await fetchWithAuth(
    `${API_URL}/payments/aggregate/sankey`,
    { method: "POST", body }
  );
  return response.json();
}

export async function fetchSumsForRanges(ranges) {
  const response = await fetchWithAuth(
    `${API_URL}/payments/sums`,
    { method: "POST", body: ranges }
  );
  return response.json();
}

export async function uploadPaymentFiles(filesWithTypes) {
  const formData = new FormData();
  filesWithTypes.forEach(({ file, type }) => {
    formData.append("files", file);
    formData.append("types", type);
  });
  const response = await fetchWithAuth(
    `${API_URL}/payments/import`,
    { method: "POST", body: formData, isForm: true, headers: {} }
  );
  return response.json();
}

export async function downloadAllPayments() {
  const response = await fetchWithAuth(`${API_URL}/payments/download`);
  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const dateStr = new Date().toISOString().slice(0, 10);
  a.download = `payments_${dateStr}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

export async function submitCustomPayment(payment) {
  const response = await fetchWithAuth(
    `${API_URL}/payments`,
    { method: "POST", body: payment }
  );
  return response.json();
}

export async function deletePayments(ids) {
  const response = await fetchWithAuth(
    `${API_URL}/payments/delete`,
    { method: "POST", body: { ids } }
  );
  return response.json();
}

// loginUser and registerUser do not require token validity check
export async function loginUser(username, password) {
  const response = await fetch(`${API_URL}/auth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ username, password }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || "Login failed");
  }
  const data = await response.json();
  localStorage.setItem("token", data.access_token);
  return data;
}

export async function registerUser(username, password) {
  const response = await fetch(`${API_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || "Registration failed");
  }
  return response.json();
}

export async function deleteUserAccount() {
  const response = await fetchWithAuth(
    `${API_URL}/auth/delete`,
    { method: "DELETE" }
  );
  return response.json();
}

export async function changeUsername(newUsername) {
  const response = await fetchWithAuth(
    `${API_URL}/auth/change-username`,
    { method: "POST", body: { new_username: newUsername } }
  );
  return response.json();
}

export async function changePassword(newPassword) {
  const response = await fetchWithAuth(
    `${API_URL}/auth/change-password`,
    { method: "POST", body: { new_password: newPassword } }
  );
  return response.json();
}
