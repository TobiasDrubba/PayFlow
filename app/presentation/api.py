# app/presentation/api.py
from datetime import datetime
from enum import Enum
from typing import List

from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import HTMLResponse

from app.domain.models import Payment
from app.domain.services import list_payments


class PaymentResponse(BaseModel):
    id: str
    date: datetime
    amount: float
    currency: str
    merchant: str
    auto_category: str
    source: str
    type: str
    note: str = ""
    cust_category: str = ""

    @staticmethod
    def from_domain(p: Payment) -> "PaymentResponse":
        return PaymentResponse(
            id=p.id,
            date=p.date,
            amount=p.amount,
            currency=p.currency,
            merchant=p.merchant,
            auto_category=p.auto_category,
            source=p.source.value if isinstance(p.source, Enum) else str(p.source),
            type=p.type.value,
            note=p.note or "",
            cust_category=p.cust_category,
        )


app = FastAPI(title="Payment API", version="1.0.0")


@app.get("/payments", response_model=List[PaymentResponse])
def get_all_payments_endpoint() -> List[PaymentResponse]:
    """
    Returns all existing payments from persistent storage.
    """
    payments = list_payments()
    return [PaymentResponse.from_domain(p) for p in payments]

@app.get("/payments/table", response_class=HTMLResponse)
def payments_table():
    """
    A modern HTML table that consumes the /payments JSON endpoint.
    """
    html = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Payments</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    .sortable:hover { cursor: pointer; opacity: 0.8; }
    .badge { @apply inline-block rounded px-2 py-0.5 text-xs font-medium; }
  </style>
</head>
<body class="bg-gray-50 text-gray-900">
  <div class="max-w-7xl mx-auto p-6">
    <div class="flex items-center justify-between mb-4">
      <h1 class="text-2xl font-semibold">Payments</h1>
      <a href="/payments" class="text-sm text-blue-600 hover:underline">View JSON</a>
    </div>

    <div class="bg-white shadow-sm rounded-lg p-4">
      <div class="flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between mb-3">
        <input
          id="search"
          type="text"
          placeholder="Search by merchant, auto category, type, note, currency, source, or id..."
          class="w-full sm:w-80 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <div class="text-sm text-gray-500">
          <span id="count">0</span> records
        </div>
      </div>

      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-100">
            <tr>
              <th class="px-3 py-2 text-left text-xs font-medium text-gray-600 uppercase tracking-wider sortable" data-key="date">Date</th>
              <th class="px-3 py-2 text-left text-xs font-medium text-gray-600 uppercase tracking-wider sortable" data-key="amount">Amount</th>
              <th class="px-3 py-2 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">Currency</th>
              <th class="px-3 py-2 text-left text-xs font-medium text-gray-600 uppercase tracking-wider sortable" data-key="merchant">Merchant</th>
              <th class="px-3 py-2 text-left text-xs font-medium text-gray-600 uppercase tracking-wider sortable" data-key="auto_category">Auto Category</th>
              <th class="px-3 py-2 text-left text-xs font-medium text-gray-600 uppercase tracking-wider sortable" data-key="type">Type</th>
              <th class="px-3 py-2 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">Source</th>
              <th class="px-3 py-2 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">Note</th>
              <th class="px-3 py-2 text-left text-xs font-medium text-gray-600 uppercase tracking-wider sortable" data-key="cust_category">Custom Category</th>
              <th class="px-3 py-2 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">ID</th>
            </tr>
          </thead>
          <tbody id="tbody" class="bg-white divide-y divide-gray-100"></tbody>
        </table>
      </div>
    </div>
  </div>

  <script>
    const state = {
      data: [],
      filtered: [],
      sortKey: 'date',
      sortDir: 'desc',
    };

    const tbody = document.getElementById('tbody');
    const search = document.getElementById('search');
    const count = document.getElementById('count');

    function formatDate(iso) {
      // iso can be ISO string or date-like; fallback to displaying raw
      try {
        const d = new Date(iso);
        if (isNaN(d.getTime())) return iso;
        return d.toLocaleString();
      } catch { return iso; }
    }

    function formatAmount(v, currency) {
      const num = Number(v);
      if (isNaN(num)) return v;
      const sign = num < 0 ? '-' : '';
      return sign + Math.abs(num).toFixed(2) + ' ' + (currency || '');
    }

    function badge(color, text) {
      const colors = {
        blue: 'bg-blue-100 text-blue-800',
        gray: 'bg-gray-100 text-gray-800',
        emerald: 'bg-emerald-100 text-emerald-800',
        amber: 'bg-amber-100 text-amber-800',
        rose: 'bg-rose-100 text-rose-800',
        violet: 'bg-violet-100 text-violet-800',
      };
      const cls = colors[color] || colors.gray;
      return '<span class="badge ' + cls + '">' + (text || '—') + '</span>';
    }

    function categoryColor(cat) {
      const key = (cat || '').toLowerCase();
      if (key.includes('income')) return 'emerald';
      if (key.includes('expense') || key.includes('支')) return 'rose';
      if (key.includes('transfer')) return 'amber';
      return 'blue';
    }

    function typeColor(t) {
      const key = (t || '').toLowerCase();
      if (key === 'income') return 'emerald';
      if (key === 'expense') return 'rose';
      return 'gray';
    }

    function sourceColor(src) {
      const key = (src || '').toLowerCase();
      if (key.includes('alipay')) return 'violet';
      if (key.includes('wechat')) return 'emerald';
      return 'gray';
    }

    function render() {
      const rows = state.filtered.map(p => {
        return `
          <tr class="hover:bg-gray-50">
            <td class="px-3 py-2 whitespace-nowrap text-sm text-gray-700">${formatDate(p.date)}</td>
            <td class="px-3 py-2 whitespace-nowrap text-sm font-medium ${Number(p.amount) < 0 ? 'text-rose-600' : 'text-gray-900'}">
              ${formatAmount(p.amount, p.currency)}
            </td>
            <td class="px-3 py-2 whitespace-nowrap text-sm text-gray-700">${p.currency || ''}</td>
            <td class="px-3 py-2 whitespace-nowrap text-sm text-gray-700">${p.merchant || ''}</td>
            <td class="px-3 py-2 whitespace-nowrap text-sm">${badge(categoryColor(p.auto_category), p.auto_category)}</td>
            <td class="px-3 py-2 whitespace-nowrap text-sm">${badge(typeColor(p.type), p.type)}</td>
            <td class="px-3 py-2 whitespace-nowrap text-sm">${badge(sourceColor(p.source), p.source || '—')}</td>
            <td class="px-3 py-2 text-sm text-gray-700 max-w-xs truncate" title="${(p.note || '').replace(/"/g, '&quot;')}">${p.note || ''}</td>
            <td class="px-3 py-2 whitespace-nowrap text-sm text-gray-700">${p.cust_category || ''}</td>
            <td class="px-3 py-2 text-xs text-gray-500">${p.id || ''}</td>
          </tr>
        `;
      }).join('');
      tbody.innerHTML = rows;
      count.textContent = state.filtered.length;
    }

    function applySearch() {
      const q = (search.value || '').toLowerCase().trim();
      if (!q) {
        state.filtered = [...state.data];
      } else {
        state.filtered = state.data.filter(p => {
          return [
            p.merchant, p.auto_category, p.type, p.cust_category, p.note, p.currency, p.source, p.id
          ].some(v => (v || '').toLowerCase().includes(q));
        });
      }
      applySort();
    }

    function applySort() {
      const k = state.sortKey;
      const dir = state.sortDir === 'asc' ? 1 : -1;
      state.filtered.sort((a, b) => {
        let va = a[k], vb = b[k];
        if (k === 'date') {
          const da = new Date(va).getTime(); const db = new Date(vb).getTime();
          return (da - db) * dir;
        }
        if (k === 'amount') {
          return (Number(va) - Number(vb)) * dir;
        }
        return String(va || '').localeCompare(String(vb || '')) * dir;
      });
      render();
    }

    function bindSorting() {
      document.querySelectorAll('th.sortable').forEach(th => {
        th.addEventListener('click', () => {
          const key = th.dataset.key;
          if (state.sortKey === key) {
            state.sortDir = state.sortDir === 'asc' ? 'desc' : 'asc';
          } else {
            state.sortKey = key;
            state.sortDir = 'asc';
          }
          applySort();
        });
      });
    }

    async function load() {
      try {
        const res = await fetch('/payments');
        const data = await res.json();
        state.data = Array.isArray(data) ? data : [];
        state.filtered = [...state.data];
        bindSorting();
        applySort();
      } catch (e) {
        tbody.innerHTML = '<tr><td class="px-3 py-2 text-sm text-rose-600">Failed to load payments.</td></tr>';
      }
    }

    search.addEventListener('input', () => applySearch());
    load();
  </script>
</body>
</html>
    """.strip()
    return HTMLResponse(content=html, status_code=200)
