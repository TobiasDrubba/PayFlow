const API_URL = process.env.REACT_APP_API_URL;
if (!API_URL) {
  throw new Error("REACT_APP_API_URL environment variable is not set");
}

export async function fetchPayments() {
  const response = await fetch(`${API_URL}/payments`);
  if (!response.ok) throw new Error("Failed to fetch payments");
  return response.json();
}

export async function fetchCategories() {
  const response = await fetch(`${API_URL}/categories`);
  if (!response.ok) throw new Error("Failed to fetch categories");
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

export async function fetchAggregation({ start_date, end_date } = {}) {
  const url = `${API_URL}/payments/aggregate/sankey`;
  const body = {};
  if (start_date) body.start_date = start_date;
  if (end_date) body.end_date = end_date;
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error("Failed to fetch aggregation data");
  return response.json();
}

export async function fetchSumsForRanges(ranges) {
  const response = await fetch(`${API_URL}/payments/sums`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(ranges),
  });
  if (!response.ok) throw new Error("Failed to fetch sums for ranges");
  return response.json();
}

export async function uploadPaymentFiles(filesWithTypes) {
  const formData = new FormData();
  filesWithTypes.forEach(({ file, type }) => {
    formData.append("files", file);
    formData.append("types", type);
  });
  const response = await fetch(`${API_URL}/payments/import`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || "Upload failed");
  }
  return response.json();
}
