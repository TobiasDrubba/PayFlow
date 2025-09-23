const API_URL = "http://localhost:8000"; // adjust to your backend URL/port

export async function fetchPayments() {
  const response = await fetch(`${API_URL}/payments`);
  if (!response.ok) throw new Error("Failed to fetch payments");
  return response.json();
}
