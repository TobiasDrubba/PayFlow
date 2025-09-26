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
