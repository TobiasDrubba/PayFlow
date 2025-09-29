const API_URL = "http://localhost:8000"; // adjust to your backend URL/port

export async function fetchPayments() {
  const response = await fetch(`${API_URL}/payments`);
  if (!response.ok) throw new Error("Failed to fetch payments");
  return response.json();
}

export async function fetchCategories() {
  const response = await fetch("http://localhost:8000/categories");
  if (!response.ok) throw new Error("Failed to fetch categories");
  return response.json();
}

export async function addCategory(name) {
  const response = await fetch("http://localhost:8000/categories", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!response.ok) throw new Error("Failed to add category");
  return response.json();
}

export async function updatePaymentCategory(paymentId, custCategory, allForMerchant = false) {
  const response = await fetch(`${API_URL}/payments/${paymentId}/category`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cust_category: custCategory, all_for_merchant: allForMerchant }),
  });
  if (!response.ok) throw new Error("Failed to update payment category");
  return response.json();
}

export async function fetchCategoryTree() {
  const response = await fetch(`${API_URL}/categories/tree`);
  if (!response.ok) throw new Error("Failed to fetch category tree");
  return response.json();
}

export async function updateCategoryTree(tree) {
  const response = await fetch(`${API_URL}/categories/tree`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tree }),
  });
  if (!response.ok) throw new Error("Failed to update category tree");
  return response.json();
}
