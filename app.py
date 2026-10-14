from __future__ import annotations

import os
import sqlite3
import tempfile
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Generator

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
from jinja2 import DictLoader

STORE_NAME = "Green Basket Grocery"
STORE_ADDRESS = "123 Market Street"
CURRENCY = "₹"
TAX_RATE = 5.0
DISCOUNT_TIERS = [(2000, 15), (1000, 10), (500, 5)]

app = Flask(__name__)
app.secret_key = "replace-this-with-a-random-secret-key"
default_database = (
    Path(tempfile.gettempdir()) / "grocery.db"
    if os.environ.get("VERCEL")
    else Path(__file__).with_name("grocery.db")
)
app.config["DATABASE"] = os.environ.get("DATABASE_PATH", str(default_database))

SAMPLE_PRODUCTS = [
    ("Rice", 60.00, 100, "kg"),
    ("Flour", 45.00, 80, "kg"),
    ("Sugar", 42.00, 75, "kg"),
    ("Milk", 30.00, 60, "ltr"),
    ("Eggs", 7.00, 120, "pc"),
    ("Tomato", 35.00, 50, "kg"),
    ("Potato", 28.00, 90, "kg"),
    ("Onion", 32.00, 70, "kg"),
    ("Oil", 150.00, 40, "ltr"),
    ("Tea", 220.00, 25, "kg"),
    ("Bread", 40.00, 35, "pc"),
    ("Salt", 20.00, 45, "kg"),
]

TEMPLATES = {
    "base.html": """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}{{ store_name }}{% endblock %}</title>
  <style>
    :root {
      --green: #126447;
      --green-dark: #0b4633;
      --green-light: #e8f4ed;
      --green-soft: #f1f8f3;
      --ink: #192f27;
      --muted: #718078;
      --border: #e0e8e2;
      --danger: #b42318;
      --surface: #ffffff;
      --bg: #f5f7f3;
      --shadow: 0 8px 24px rgba(24, 54, 38, 0.055);
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      color: var(--ink);
      background: var(--bg);
      font: 14px/1.6 Inter, -apple-system, BlinkMacSystemFont,
            "Segoe UI", sans-serif;
      -webkit-font-smoothing: antialiased;
    }

    nav {
      background: linear-gradient(135deg, #0b4633, #126447);
      color: white;
      padding: 0 28px;
      box-shadow: 0 3px 15px rgba(8, 50, 35, 0.12);
    }

    .nav-inner {
      max-width: 1440px;
      min-height: 72px;
      margin: auto;
      display: flex;
      align-items: center;
      gap: 25px;
    }

    .brand {
      margin-right: auto;
      color: white;
      text-decoration: none;
      font-size: 19px;
      font-weight: 800;
      letter-spacing: -0.5px;
      white-space: nowrap;
    }

    nav a:not(.brand) {
      position: relative;
      color: #e2f1e8;
      text-decoration: none;
      font-weight: 600;
      font-size: 13px;
      white-space: nowrap;
      transition: color 0.2s ease;
    }

    nav a:not(.brand):hover {
      color: white;
    }

    nav a:not(.brand)::after {
      content: "";
      position: absolute;
      left: 0;
      right: 100%;
      bottom: -8px;
      height: 2px;
      background: #a8e2bd;
      transition: right 0.2s ease;
    }

    nav a:not(.brand):hover::after {
      right: 0;
    }

    main {
      max-width: 1440px;
      margin: 34px auto;
      padding: 0 28px 48px;
      min-height: calc(100vh - 110px);
    }

    h1 {
      margin: 0 0 24px;
      font-size: clamp(25px, 3vw, 32px);
      line-height: 1.25;
      font-weight: 800;
      letter-spacing: -1px;
      color: #173b2d;
    }

    h2 {
      font-size: 17px;
      font-weight: 750;
      letter-spacing: -0.25px;
      margin: 0 0 18px;
    }

    h3 {
      font-size: 15px;
      font-weight: 750;
    }

    p {
      margin-top: 0;
    }

    .card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 24px;
      box-shadow: var(--shadow);
      min-width: 0;
    }

    .grid {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 22px;
      align-items: start;
    }

    .stack {
      display: grid;
      gap: 22px;
    }

    label {
      display: block;
      font-weight: 650;
      font-size: 13px;
      margin-bottom: 7px;
      color: #354b3f;
    }

    input,
    select,
    textarea,
    button {
      font: inherit;
    }

    input[type="text"],
    input[type="number"],
    input[type="search"],
    input[type="tel"],
    select,
    textarea {
      width: 100%;
      min-height: 42px;
      padding: 10px 12px;
      border: 1px solid #d5e0d8;
      border-radius: 9px;
      color: var(--ink);
      background: #fff;
      transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }

    input:focus,
    select:focus,
    textarea:focus {
      outline: none;
      border-color: #21865e;
      box-shadow: 0 0 0 3px rgba(33, 134, 94, 0.12);
    }

    .field {
      margin-bottom: 17px;
    }

    .button,
    button.button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 7px;
      min-height: 40px;
      border: 1px solid transparent;
      border-radius: 9px;
      background: var(--green);
      color: white;
      font-weight: 700;
      padding: 9px 16px;
      text-decoration: none;
      cursor: pointer;
      transition: background 0.2s ease, transform 0.15s ease;
    }

    .button:hover {
      background: var(--green-dark);
      transform: translateY(-1px);
    }

    .button.secondary {
      background: #f0f5f1;
      color: #284536;
      border-color: #dce7df;
    }

    .button.secondary:hover {
      background: #e3eee6;
    }

    .button.danger {
      background: #fff1ef;
      color: var(--danger);
      border-color: #f2d1cc;
    }

    .button.danger:hover {
      background: #ffe3df;
    }

    .button.small {
      min-height: 32px;
      padding: 6px 11px;
      font-size: 12px;
      border-radius: 7px;
    }

    .button:disabled {
      opacity: 0.55;
      cursor: not-allowed;
      transform: none;
    }

    .actions {
      display: flex;
      gap: 9px;
      flex-wrap: wrap;
      align-items: center;
    }

    .table-wrap {
      overflow-x: auto;
      width: 100%;
      border-radius: 9px;
    }

    table {
      width: 100%;
      border-collapse: separate;
      border-spacing: 0;
      font-size: 13px;
    }

    th,
    td {
      text-align: left;
      padding: 13px 12px;
      border-bottom: 1px solid #e9eee9;
      vertical-align: middle;
    }

    th {
      background: #f5f8f5;
      color: #64756b;
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.055em;
      white-space: nowrap;
    }

    th:first-child {
      border-radius: 8px 0 0 0;
    }

    th:last-child {
      border-radius: 0 8px 0 0;
    }

    tbody tr {
      transition: background 0.15s ease;
    }

    tbody tr:hover {
      background: #f8fbf8;
    }

    tbody tr:last-child td {
      border-bottom: 0;
    }

    td.numeric,
    th.numeric {
      text-align: right;
      white-space: nowrap;
    }

    td input {
      min-width: 85px;
    }

    .muted {
      color: var(--muted);
    }

    .price {
      color: var(--green-dark);
      font-weight: 800;
      white-space: nowrap;
    }

    .product-list {
      max-height: 590px;
      overflow: auto;
      padding-right: 3px;
    }

    .product-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      padding: 14px 8px;
      border-bottom: 1px solid #edf1ed;
      border-radius: 8px;
    }

    .product-row:hover {
      background: var(--green-soft);
    }

    .product-row:last-child {
      border-bottom: 0;
    }

    .product-detail {
      min-width: 0;
    }

    .product-name {
      font-weight: 750;
      font-size: 14px;
    }

    .product-meta {
      color: var(--muted);
      font-size: 12px;
      margin-top: 3px;
    }

    .qty-input {
      width: 82px !important;
      min-height: 34px !important;
      padding: 6px 7px !important;
    }

    .totals {
      width: min(100%, 390px);
      margin: 17px 0 0 auto;
      padding: 15px;
      background: #f7faf7;
      border: 1px solid #e8eee9;
      border-radius: 12px;
    }

    .total-line {
      display: flex;
      justify-content: space-between;
      padding: 7px 0;
      gap: 16px;
    }

    .total-line.grand {
      border-top: 1px solid #d8e4da;
      margin-top: 7px;
      padding-top: 14px;
      font-weight: 850;
      font-size: 20px;
      color: var(--green-dark);
    }

    .hint {
      min-height: 24px;
      margin-top: 9px;
      color: var(--green-dark);
      font-size: 12px;
      font-weight: 650;
    }

    .flash {
      padding: 13px 16px;
      border-radius: 10px;
      margin-bottom: 17px;
      background: #eaf6ee;
      border: 1px solid #cce5d3;
      color: #175d3d;
      font-weight: 600;
    }

    .flash.error {
      background: #fff1ef;
      border-color: #f2cbc6;
      color: #8e1b13;
    }

    .summary {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
      gap: 17px;
      margin-bottom: 22px;
    }

    .summary .card {
      min-width: 0;
      border-top: 3px solid var(--green);
    }

    .summary-value {
      color: var(--green-dark);
      font-size: 27px;
      font-weight: 850;
      letter-spacing: -0.7px;
      overflow-wrap: anywhere;
    }

    .low-stock {
      color: var(--danger);
      font-weight: 750;
    }

    .inline-form {
      display: flex;
      gap: 8px;
      align-items: center;
    }

    .empty {
      padding: 24px 12px;
      text-align: center;
      color: var(--muted);
    }

    a {
      color: var(--green);
    }

    @media (max-width: 900px) {
      .nav-inner {
        gap: 16px;
      }

      nav {
        padding: 0 18px;
      }

      main {
        padding-left: 18px;
        padding-right: 18px;
      }
    }

    @media (max-width: 760px) {
      .nav-inner {
        padding: 14px 0;
        gap: 14px 18px;
        flex-wrap: wrap;
      }

      .brand {
        flex-basis: 100%;
        font-size: 18px;
      }

      nav a:not(.brand) {
        font-size: 12px;
      }

      main {
        margin-top: 24px;
        padding-left: 14px;
        padding-right: 14px;
      }

      .grid {
        grid-template-columns: minmax(0, 1fr);
      }

      h1 {
        font-size: 25px;
      }

      .card {
        padding: 17px;
        border-radius: 13px;
      }

      th,
      td {
        padding: 10px 9px;
      }

      .summary {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }

      .summary .card {
        padding: 15px;
      }

      .summary-value {
        font-size: 22px;
      }
    }

    @media (max-width: 420px) {
      .summary {
        grid-template-columns: 1fr;
      }

      .actions .button {
        max-width: 100%;
      }
    }

    @media print {
      nav,
      .no-print,
      .flash {
        display: none !important;
      }

      body {
        background: white;
      }

      main {
        max-width: none;
        margin: 0;
        padding: 0;
      }

      .card {
        border: 0;
        box-shadow: none;
        padding: 0;
      }
    }
    .badge {
    display: inline-block;
    padding: 5px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
    white-space: nowrap;
}

.badge.danger {
    background: #fde8e7;
    color: #a61b1b;
}

.badge.warning {
    background: #fff3cd;
    color: #805b00;
}

.badge.success {
    background: #e3f5e8;
    color: #176b43;
}

.actions {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
}

.actions form {
    margin: 0;
}

@media (max-width: 700px) {
    .actions {
        align-items: stretch;
        flex-direction: column;
    }
}
/* Premium billing dashboard */
.billing-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 16px;
    margin-bottom: 24px;
}

.billing-header h1 {
    margin: 4px 0 8px;
}

.eyebrow {
    color: #176b43;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 1.5px;
    margin: 0 0 6px;
}

.billing-status {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 10px 14px;
    border-radius: 999px;
    background: #eaf5ee;
    color: #176b43;
    font-size: 12px;
    font-weight: 700;
}

.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #20a464;
}

.billing-layout {
    align-items: start;
    gap: 22px;
}

.product-panel,
.cart-panel {
    min-width: 0;
}

.section-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 20px;
}

.section-heading h2 {
    margin: 0;
}

.count-pill {
    display: inline-block;
    padding: 7px 10px;
    border-radius: 999px;
    background: #eaf5ee;
    color: #176b43;
    font-size: 11px;
    font-weight: 700;
    white-space: nowrap;
}

.search-field {
    margin-bottom: 18px;
}

.product-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.product-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 14px;
    border: 1px solid #e5eee8;
    border-radius: 12px;
    background: #fff;
    transition: border-color 0.2s, background 0.2s;
}

.product-row:hover {
    border-color: #8bbda0;
    background: #f8fcf9;
}

.product-detail {
    min-width: 0;
}

.product-name {
    font-weight: 750;
    overflow-wrap: anywhere;
}

.product-meta {
    margin-top: 5px;
    font-size: 13px;
    font-weight: 700;
    color: #176b43;
}

.stock-note {
    margin-top: 4px;
    font-size: 11px;
    color: #718078;
}

.billing-form-section {
    padding-bottom: 16px;
    border-bottom: 1px solid #e5eee8;
}

.payment-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
}

.field-note {
    font-size: 11px;
    margin: 5px 0 0;
}

.cart-table-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 8px;
    margin: 20px 0 12px;
}

.cart-table-heading h3 {
    margin: 0;
}

.cart-table-heading .muted {
    font-size: 11px;
}

.cart-panel .table-wrap {
    width: 100%;
    overflow-x: auto;
}

.cart-panel table {
    width: 100%;
    border-collapse: collapse;
}

.cart-panel th,
.cart-panel td {
    padding: 12px 8px;
    vertical-align: middle;
}

.cart-panel th {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    color: #718078;
}

.cart-panel .qty-input {
    width: 76px;
    min-width: 58px;
}

.billing-totals {
    margin-top: 20px;
    padding: 16px;
    border-radius: 14px;
    background: #f5faf6;
}

.billing-totals .total-line {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    padding: 8px 0;
}

.billing-totals .grand {
    margin-top: 8px;
    padding-top: 16px;
    border-top: 1px dashed #bfd6c6;
    color: #145b38;
    font-size: 19px;
    font-weight: 800;
}

.billing-totals .hint {
    margin-top: 12px;
    padding: 10px;
    border-radius: 8px;
    background: #e5f4e9;
    color: #176b43;
    font-size: 12px;
}

.billing-actions {
    display: flex;
    gap: 12px;
    margin-top: 18px;
}

.billing-actions button {
    flex: 1;
}

@media (max-width: 700px) {
    .billing-header {
        align-items: flex-start;
    }

    .billing-layout {
        grid-template-columns: minmax(0, 1fr);
    }

    .payment-grid {
        grid-template-columns: minmax(0, 1fr);
        gap: 0;
    }

    .billing-actions {
        flex-direction: column;
    }

    .billing-status {
        font-size: 11px;
    }

    .billing-totals .grand {
        font-size: 17px;
    }
}
  </style>
  {% block head %}{% endblock %}
</head>
<body>
  <nav class="no-print"><div class="nav-inner">
    <a class="brand" href="{{ url_for('index') }}">{{ store_name }}</a>
    <a href="{{ url_for('index') }}">New Bill</a>
    <a href="{{ url_for('products') }}">Products</a>
    <a href="{{ url_for('customers') }}">Customers</a>
    <a href="{{ url_for('sales_report') }}">Sales Reports</a>
    <a href="{{ url_for('bills') }}">Bill History</a>
  </div></nav>
  <main>
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% for category, message in messages %}<div class="flash {{ 'error' if category == 'error' else '' }}">{{ message }}</div>{% endfor %}
    {% endwith %}
    {% block content %}{% endblock %}
  </main>
  {% block scripts %}{% endblock %}
</body>
</html>
""",
    "billing.html": """
{% extends "base.html" %}

{% block title %}New Bill · {{ store_name }}{% endblock %}

{% block content %}
<div class="billing-header">
    <div>
        <p class="eyebrow">POINT OF SALE</p>
        <h1>New Bill</h1>
        <p class="muted">Create a sale, collect payment, and manage customer credit.</p>
    </div>
    <div class="billing-status">
        <span class="status-dot"></span>
        Billing terminal ready
    </div>
</div>

<div class="grid billing-layout">

    <!-- LEFT: PRODUCT INVENTORY -->
    <section class="card product-panel">
        <div class="section-heading">
            <div>
                <p class="eyebrow">INVENTORY</p>
                <h2>Choose Products</h2>
            </div>
            <span class="count-pill">{{ products|length }} products</span>
        </div>

        <div class="field search-field">
            <label for="product-search">Find a product</label>
            <input
                id="product-search"
                type="search"
                placeholder="Search by product name..."
                aria-label="Search products"
            >
        </div>

        <div id="product-list" class="product-list">
            {% for product in products %}
            <div class="product-row" data-search="{{ product.name|lower }}">
                <div class="product-detail">
                    <div class="product-name">{{ product.name }}</div>
                    <div class="product-meta">
                        {{ currency }}{{ '%.2f'|format(product.price) }}
                        / {{ product.unit }}
                    </div>
                    <div class="stock-note">
                        {{ '%g'|format(product.stock) }} {{ product.unit }} available
                    </div>
                </div>

               <button
    class="button small add-product"
    type="button"
    data-id="{{ product.id }}"
>
    + Add
</button>
            </div>
            {% else %}
            <div class="empty">No products are currently in stock.</div>
            {% endfor %}
        </div>
    </section>

    <!-- RIGHT: BILLING CART -->
    <section class="card cart-panel">
        <div class="section-heading">
            <div>
                <p class="eyebrow">CURRENT TRANSACTION</p>
                <h2>Shopping Cart</h2>
            </div>
            <span class="count-pill">New sale</span>
        </div>

        <div class="billing-form-section">
            <div class="field">
                <label for="customer-id">Registered customer</label>
                <select id="customer-id">
                    <option value="">Walk-in customer</option>
                    {% for customer in customers %}
                    <option value="{{ customer.id }}">
                        {{ customer.name }}{% if customer.phone %} — {{ customer.phone }}{% endif %}
                    </option>
                    {% endfor %}
                </select>
            </div>

            <div class="field">
                <label for="customer">Walk-in customer name (optional)</label>
                <input
                    id="customer"
                    type="text"
                    maxlength="120"
                    placeholder="Enter customer name"
                >
            </div>

            <div class="payment-grid">
                <div class="field">
                    <label for="paid-amount">Amount paid now (₹)</label>
                    <input
                        id="paid-amount"
                        type="number"
                        min="0"
                        step="0.01"
                        value="0"
                        required
                    >
                    <p class="muted field-note">Enter 0 for full Udhar.</p>
                </div>

                <div class="field">
                    <label for="payment-method">Payment method</label>
                    <select id="payment-method">
                        <option value="Cash">Cash</option>
                        <option value="UPI">UPI</option>
                        <option value="Card">Card</option>
                    </select>
                </div>
            </div>
        </div>

        <div class="cart-table-heading">
            <h3>Bill Items</h3>
            <span class="muted">Adjust quantities below</span>
        </div>

        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Item</th>
                        <th>Qty</th>
                        <th class="numeric">Amount</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody id="cart-body">
                    <tr>
                        <td colspan="4" class="empty">Your cart is empty.</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="totals billing-totals">
            <div class="total-line">
                <span>Subtotal</span>
                <strong id="subtotal">{{ currency }}0.00</strong>
            </div>

            <div class="total-line">
                <span>Discount (<span id="discount-pct">0</span>%)</span>
                <strong id="discount">{{ currency }}0.00</strong>
            </div>

            <div class="total-line">
                <span>Tax ({{ '%.2f'|format(tax_rate) }}%)</span>
                <strong id="tax">{{ currency }}0.00</strong>
            </div>

            <div class="total-line grand">
                <span>Total Payable</span>
                <span id="total">{{ currency }}0.00</span>
            </div>

            <div id="discount-hint" class="hint" aria-live="polite">
                Add {{ currency }}500.00 more to get 5% off
            </div>
        </div>

        <div class="actions billing-actions">
            <button id="clear-cart" class="button secondary" type="button">
                Clear Cart
            </button>
            <button id="generate-bill" class="button" type="button" disabled>
                Generate Bill →
            </button>
        </div>

        <div
            id="cart-error"
            class="flash error"
            role="alert"
            hidden
            style="margin-top:14px;margin-bottom:0"
        ></div>
    </section>
</div>
{% endblock %}
{% block scripts %}
<script>
(() => {
  const products = {{ products|tojson }};
  const tiers = {{ discount_tiers|tojson }};
  const currency = {{ currency|tojson }};
  const taxRate = {{ tax_rate|tojson }};
  const cart = new Map();
  const body = document.getElementById("cart-body");
  const errorBox = document.getElementById("cart-error");

  const roundMoney = value =>
    Math.round((value + Number.EPSILON) * 100) / 100;

  const money = value => currency + roundMoney(value).toFixed(2);

  const discountFor = subtotal =>
    tiers.find(([minimum]) => subtotal >= minimum)?.[1] || 0;

  function updateTotals() {
    let subtotal = 0;

    for (const item of cart.values()) {
      subtotal += roundMoney(item.product.price * item.qty);
    }

    subtotal = roundMoney(subtotal);

    const pct = discountFor(subtotal);
    const discount = roundMoney(subtotal * pct / 100);
    const taxable = roundMoney(subtotal - discount);
    const tax = roundMoney(taxable * taxRate / 100);

    document.getElementById("subtotal").textContent = money(subtotal);
    document.getElementById("discount-pct").textContent = pct;
    document.getElementById("discount").textContent = money(discount);
    document.getElementById("tax").textContent = money(tax);
    document.getElementById("total").textContent =
      money(taxable + tax);

    document.getElementById("generate-bill").disabled = cart.size === 0;

    const next = tiers.slice().reverse()
      .find(([minimum]) => subtotal < minimum);

    document.getElementById("discount-hint").textContent = next
      ? `Add ${money(next[0] - subtotal)} more to get ${next[1]}% off`
      : "Maximum discount applied";
  }

  function renderCart() {
    body.replaceChildren();

    if (cart.size === 0) {
      const row = document.createElement("tr");
      const cell = document.createElement("td");

      cell.colSpan = 4;
      cell.className = "empty";
      cell.textContent = "Your cart is empty.";

      row.append(cell);
      body.append(row);
    } else {
      for (const [id, item] of cart) {
        const row = document.createElement("tr");

        const name = document.createElement("td");
        name.textContent = item.product.name;

        const quantityCell = document.createElement("td");
        const quantity = document.createElement("input");

        quantity.type = "number";
        quantity.min = "0.01";
        quantity.step = "any";
        quantity.max = String(item.product.stock);
        quantity.value = String(item.qty);
        quantity.className = "qty-input";
        quantity.setAttribute(
          "aria-label",
          `Quantity of ${item.product.name}`
        );

        quantity.addEventListener("input", () => {
          const value = Number(quantity.value);

          if (
            Number.isFinite(value) &&
            value > 0 &&
            value <= item.product.stock
          ) {
            item.qty = value;
            amount.textContent = money(item.product.price * value);
            updateTotals();
          }
        });

        quantityCell.append(quantity);

        const amount = document.createElement("td");
        amount.className = "numeric";
        amount.textContent = money(item.product.price * item.qty);

        const action = document.createElement("td");
        const remove = document.createElement("button");

        remove.type = "button";
        remove.className = "button danger small";
        remove.textContent = "Remove";
        remove.setAttribute(
          "aria-label",
          `Remove ${item.product.name}`
        );

        remove.addEventListener("click", () => {
          cart.delete(id);
          renderCart();
        });

        action.append(remove);
        row.append(name, quantityCell, amount, action);
        body.append(row);
      }
    }

    updateTotals();
  }

  document.querySelectorAll(".add-product").forEach(button => {
    button.addEventListener("click", () => {
      const product = products.find(
        item => item.id === Number(button.dataset.id)
      );

      if (!product) return;

      const current = cart.get(product.id);

      if (current) {
        if (current.qty + 1 > product.stock) {
          errorBox.textContent = "Not enough stock available.";
          errorBox.hidden = false;
          return;
        }

        current.qty += 1;
      } else {
        cart.set(product.id, { product, qty: 1 });
      }

      errorBox.hidden = true;
      renderCart();
    });
  });

  document.getElementById("product-search")
    .addEventListener("input", event => {
      const term = event.target.value.trim().toLowerCase();

      document.querySelectorAll(".product-row").forEach(row => {
        row.hidden = !row.dataset.search.includes(term);
      });
    });

  document.getElementById("clear-cart").addEventListener("click", () => {
    cart.clear();
    errorBox.hidden = true;
    renderCart();
  });

  document.getElementById("generate-bill")
    .addEventListener("click", async event => {
      const button = event.currentTarget;

      button.disabled = true;
      errorBox.hidden = true;

      try {
        const response = await fetch(
          {{ url_for('api_create_bill')|tojson }},
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              customer_id:
                document.getElementById("customer-id").value || null,
              customer:
                document.getElementById("customer").value.trim(),
              paid_amount:
                document.getElementById("paid-amount").value,
              payment_method:
                document.getElementById("payment-method").value,
              items: Array.from(cart, ([product_id, item]) => ({
                product_id,
                qty: item.qty
              }))
            })
          }
        );

        const result = await response.json();

        if (!response.ok) {
          throw new Error(result.error || "Could not create bill.");
        }

        window.location.href = result.redirect;
      } catch (error) {
        errorBox.textContent =
          error.message || "Could not create bill. Please try again.";

        errorBox.hidden = false;
        button.disabled = cart.size === 0;
      }
    });

  renderCart();
})();
</script>
{% endblock %}
""",
    "invoice.html": """
{% extends "base.html" %}
{% block title %}Invoice {{ '%06d'|format(bill.id) }} · {{ store_name }}{% endblock %}
{% block content %}
<div class="actions no-print" style="justify-content:flex-end;margin-bottom:16px"><button class="button" onclick="window.print()">Print Invoice</button></div>
<section class="card invoice">
  <header style="text-align:center;border-bottom:1px solid var(--border);padding-bottom:16px;margin-bottom:18px">
    <h1 style="margin-bottom:5px">{{ store_name }}</h1>
    <div class="muted">{{ store_address }}</div>
    <h2 style="margin:15px 0 0">INVOICE #{{ '%06d'|format(bill.id) }}</h2>
  </header>
  <div style="display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap;margin-bottom:18px">
    <div><strong>Date:</strong> {{ bill.created }}<br><strong>Customer:</strong> {{ bill.customer or 'Walk-in customer' }}</div>
    <div><strong>Invoice:</strong> #{{ '%06d'|format(bill.id) }}</div>
  </div>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Item</th><th class="numeric">Price</th><th class="numeric">Qty</th><th>Unit</th><th class="numeric">Amount</th></tr></thead>
      <tbody>{% for item in items %}
      <tr><td>{{ item.name }}</td><td class="numeric">{{ currency }}{{ '%.2f'|format(item.price) }}</td><td class="numeric">{{ item.qty }}</td><td>{{ item.unit }}</td><td class="numeric">{{ currency }}{{ '%.2f'|format(item.line_total) }}</td></tr>
      {% endfor %}</tbody>
    </table>
  </div>
  <div class="totals">
    <div class="total-line"><span>Subtotal</span><strong>{{ currency }}{{ '%.2f'|format(bill.subtotal) }}</strong></div>
    <div class="total-line"><span>Discount ({{ '%.0f'|format(bill.discount_pct) }}%)</span><strong>-{{ currency }}{{ '%.2f'|format(bill.discount) }}</strong></div>
    <div class="total-line"><span>Tax ({{ '%.2f'|format(tax_rate) }}%)</span><strong>{{ currency }}{{ '%.2f'|format(bill.tax) }}</strong></div>
    <div class="total-line grand"><span>Total</span><span>{{ currency }}{{ '%.2f'|format(bill.total) }}</span></div>
  </div>
  <p style="text-align:center;margin:35px 0 5px;font-weight:700">Thank you for shopping with us!</p>
</section>
{% endblock %}
""",
    "bills.html": """
{% extends "base.html" %}
{% block title %}Bill History · {{ store_name }}{% endblock %}
{% block content %}
<h1>Bill History</h1>
<div class="summary">
  <div class="card"><div class="muted">Bills today</div><div class="summary-value">{{ today_count }}</div></div>
  <div class="card"><div class="muted">Sales today</div><div class="summary-value">{{ currency }}{{ '%.2f'|format(today_sales) }}</div></div>
</div>
<section class="card">
  <h2>Latest bills <span class="muted">(up to 200)</span></h2>
  <div class="table-wrap"><table>
    <thead><tr><th>Invoice</th><th>Date</th><th>Customer</th><th class="numeric">Subtotal</th><th class="numeric">Discount</th><th class="numeric">Total</th><th></th></tr></thead>
    <tbody>
    {% for bill in bills %}
      <tr><td>#{{ '%06d'|format(bill.id) }}</td><td>{{ bill.created }}</td><td>{{ bill.customer or 'Walk-in customer' }}</td><td class="numeric">{{ currency }}{{ '%.2f'|format(bill.subtotal) }}</td><td class="numeric">{{ '%.0f'|format(bill.discount_pct) }}% · {{ currency }}{{ '%.2f'|format(bill.discount) }}</td><td class="numeric"><strong>{{ currency }}{{ '%.2f'|format(bill.total) }}</strong></td><td><a class="button small" href="{{ url_for('invoice', bill_id=bill.id) }}">View</a></td></tr>
    {% else %}<tr><td colspan="7" class="empty">No bills have been created yet.</td></tr>{% endfor %}
    </tbody>
  </table></div>
</section>
{% endblock %}
""",
    "products.html": """
{% extends "base.html" %}

{% block title %}Product Inventory · {{ store_name }}{% endblock %}

{% block content %}
<section class="card">
    <h1>Product Inventory</h1>
    <p class="muted">Manage product prices, stock levels, and inventory records.</p>

    <div class="grid">
        <div class="card">
            <p class="muted">Total Products</p>
            <h2>{{ products|length }}</h2>
        </div>

        <div class="card">
            <p class="muted">Low Stock Items</p>
            <h2>
                {{ products|selectattr("stock", "lt", 10)|list|length }}
            </h2>
            <p class="muted">Products with fewer than 10 units</p>
        </div>
    </div>
</section>

<section class="card">
    <h2>Add New Product</h2>
    <p class="muted">Enter the product details to add an item to your inventory.</p>

    <form method="post" action="{{ url_for('add_product') }}">
        <div class="grid">
            <div class="field">
                <label for="new-name">Product Name</label>
                <input id="new-name" name="name" placeholder="e.g. Rice" required maxlength="100">
            </div>

            <div class="field">
                <label for="new-price">Price ({{ currency }})</label>
                <input id="new-price" type="number" name="price" min="0" step="0.01" placeholder="0.00" required>
            </div>

            <div class="field">
                <label for="new-stock">Opening Stock</label>
                <input id="new-stock" type="number" name="stock" min="0" step="any" placeholder="Enter quantity" required>
            </div>

            <div class="field">
                <label for="new-unit">Unit</label>
                <input id="new-unit" name="unit" maxlength="20" placeholder="kg, litre, packet" required>
            </div>
        </div>

        <button class="button" type="submit">+ Add Product</button>
    </form>
</section>

<section class="card">
    <h2>Inventory Records</h2>
    <p class="muted">Edit a product's details and select Save to apply your changes.</p>

    <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th>Product</th>
                    <th>Price ({{ currency }})</th>
                    <th>Available Stock</th>
                    <th>Unit</th>
                    <th>Stock Status</th>
                    <th>Actions</th>
                </tr>
            </thead>

            <tbody>
                {% for product in products %}
                <tr>
                    <td>
                        <form
                            id="edit-product-{{ product.id }}"
                            method="post"
                            action="{{ url_for('update_product', product_id=product.id) }}"
                        ></form>

                        <input
                            form="edit-product-{{ product.id }}"
                            type="text"
                            name="name"
                            value="{{ product.name }}"
                            maxlength="100"
                            required
                            aria-label="Product name"
                        >
                    </td>

                    <td>
                        <input
                            form="edit-product-{{ product.id }}"
                            type="number"
                            name="price"
                            value="{{ '%.2f'|format(product.price) }}"
                            min="0"
                            step="0.01"
                            required
                            aria-label="Product price"
                        >
                    </td>

                    <td>
                        <input
                            form="edit-product-{{ product.id }}"
                            type="number"
                            name="stock"
                            value="{{ '%g'|format(product.stock) }}"
                            min="0"
                            step="any"
                            required
                            aria-label="Available stock"
                        >
                    </td>

                    <td>
                        <input
                            form="edit-product-{{ product.id }}"
                            type="text"
                            name="unit"
                            value="{{ product.unit }}"
                            maxlength="20"
                            required
                            aria-label="Product unit"
                        >
                    </td>

                    <td>
                        {% if product.stock == 0 %}
                            <span class="badge danger">Out of stock</span>
                        {% elif product.stock < 10 %}
                            <span class="badge warning">Low stock</span>
                        {% else %}
                            <span class="badge success">In stock</span>
                        {% endif %}
                    </td>

                    <td>
                        <div class="actions">
                            <button
                                class="button small"
                                type="submit"
                                form="edit-product-{{ product.id }}"
                            >Save</button>

                            <form
                                method="post"
                                action="{{ url_for('delete_product', product_id=product.id) }}"
                                onsubmit="return confirm('Delete this product from inventory?')"
                            >
                                <button class="button danger small" type="submit">Delete</button>
                            </form>
                        </div>
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="6" class="empty">
                        No products found. Add your first product above.
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</section>

<p><a href="{{ url_for('index') }}">← Back to Billing</a></p>
{% endblock %}
""",
"customers.html": """
    {% extends "base.html" %}

{% block title %}Customers · {{ store_name }}{% endblock %}

{% block content %}
<section class="card">
    <h1>Customer Management</h1>
    <p class="muted">Manage registered customers and collect outstanding Udhar payments.</p>

    <h2>Add New Customer</h2>

    <form method="POST" action="{{ url_for('add_customer') }}">
        <label for="customer-name">Customer Name</label>
        <input
            id="customer-name"
            type="text"
            name="name"
            placeholder="Enter customer name"
            required
        >

        <label for="customer-phone">Phone Number</label>
        <input
            id="customer-phone"
            type="tel"
            name="phone"
            placeholder="Enter phone number"
        >

        <button type="submit">+ Add Customer</button>
    </form>
</section>

<section class="card">
    <h2>Registered Customers</h2>

    {% if customers %}
    <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th>Customer</th>
                    <th>Phone</th>
                    <th>Outstanding Udhar</th>
                    <th>Collect Payment</th>
                    <th>Customer Ledger</th>
                </tr>
            </thead>
            <tbody>
                {% for customer in customers %}
                <tr>
                    <td><strong>{{ customer["name"] }}</strong></td>
                    <td>{{ customer["phone"] or "-" }}</td>
                    <td>
                        <strong>
                            ₹{{ "%.2f"|format(customer["balance"] or 0) }}
                        </strong>
                    </td>
                    <td>
                        {% if customer["balance"]|float > 0 %}
                        <form
                            method="POST"
                            action="{{ url_for('collect_udhar', customer_id=customer['id']) }}"
                        >
                            <input
                                type="number"
                                name="amount"
                                min="0.01"
                                max="{{ customer['balance'] }}"
                                step="0.01"
                                placeholder="Amount (₹)"
                                required
                            >

                            <select name="payment_method" required>
                                <option value="Cash">Cash</option>
                                <option value="UPI">UPI</option>
                                <option value="Card">Card</option>
                            </select>

                            <button type="submit">Collect</button>
                        </form>
                        {% else %}
                        <span class="muted">No dues</span>
                        {% endif %}
                    </td>
                    <td>
                        <a href="{{ url_for('customer_ledger', customer_id=customer['id']) }}">
                            View Ledger →
                        </a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% else %}
    <p>No customers registered yet. Add your first customer above.</p>
    {% endif %}
</section>

<p>
    <a href="{{ url_for('index') }}">← Back to Billing</a>
</p>
{% endblock %}
    """,
    "ledger.html": """
{% extends "base.html" %}

{% block title %}Customer Ledger · {{ store_name }}{% endblock %}

{% block content %}
<h1>Customer Ledger</h1>

<section class="card">
    <h2>{{ customer["name"] }}</h2>
    <p>Phone: {{ customer["phone"] or "Not provided" }}</p>

    <div class="totals">
        <div class="total-line grand">
            <span>Outstanding Udhar</span>
            <span>{{ currency }}{{ "%.2f"|format(balance|float) }}</span>
        </div>
    </div>

    <p>
        <a href="{{ url_for('customers') }}">Back to Customers</a>
    </p>
</section>

<section class="card">
    <h2>Bill History</h2>

    <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th>Bill ID</th>
                    <th>Date</th>
                    <th>Total</th>
                    <th>Paid</th>
                    <th>Balance Due</th>
                </tr>
            </thead>
            <tbody>
                {% for bill in bills %}
                <tr>
                    <td>#{{ bill["id"] }}</td>
                    <td>{{ bill["created"] }}</td>
                    <td>{{ currency }}{{ "%.2f"|format(bill["total"]) }}</td>
                    <td>{{ currency }}{{ "%.2f"|format(bill["paid_amount"]) }}</td>
                    <td>{{ currency }}{{ "%.2f"|format(bill["balance_due"]) }}</td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="5">No bills found for this customer.</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</section>

<section class="card">
    <h2>Payment History</h2>

    <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Bill ID</th>
                    <th>Amount Received</th>
                    <th>Payment Method</th>
                </tr>
            </thead>
            <tbody>
                {% for payment in payments %}
                <tr>
                    <td>{{ payment["created"] }}</td>
                    <td>#{{ payment["bill_id"] }}</td>
                    <td>{{ currency }}{{ "%.2f"|format(payment["amount"]) }}</td>
                    <td>{{ payment["method"] }}</td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="4">No payments recorded yet.</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</section>
{% endblock %}
""",
"reports.html": """
{% extends "base.html" %}

{% block title %}Sales Dashboard · {{ store_name }}{% endblock %}

{% block content %}
<section class="card">
    <h1>Daily Sales Dashboard</h1>
    <p class="muted">Business performance for {{ report_date }}</p>
</section>

<div class="grid">
    <section class="card">
        <p class="muted">Bills Today</p>
        <h2>{{ summary["bill_count"] }}</h2>
        <p class="muted">Total transactions</p>
    </section>

    <section class="card">
        <p class="muted">Total Sales</p>
        <h2>{{ currency }}{{ "%.2f"|format(summary["total_sales"]) }}</h2>
        <p class="muted">Value of today's bills</p>
    </section>

    <section class="card">
        <p class="muted">Money Collected</p>
        <h2>{{ currency }}{{ "%.2f"|format(summary["amount_collected"]) }}</h2>
        <p class="muted">Payments received</p>
    </section>

    <section class="card">
        <p class="muted">Udhar Added Today</p>
        <h2>{{ currency }}{{ "%.2f"|format(summary["udhar_added"]) }}</h2>
        <p class="muted">Credit given to customers</p>
    </section>
</div>

<section class="card">
    <h2>Top 5 Products Sold Today</h2>
    <p class="muted">Products ranked by today's sales performance.</p>

    <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th>Product</th>
                    <th>Quantity Sold</th>
                    <th>Sales Amount</th>
                </tr>
            </thead>
            <tbody>
                {% for product in top_products %}
                <tr>
                    <td><strong>{{ product["name"] }}</strong></td>
                    <td>{{ "%.2f"|format(product["quantity_sold"]) }}</td>
                    <td>{{ currency }}{{ "%.2f"|format(product["sales_amount"]) }}</td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="3">No sales recorded today.</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</section>

<section class="card">
    <h2>Quick Actions</h2>
    <p>Continue managing your store using these existing pages.</p>
    <p><a href="{{ url_for('index') }}">Create New Bill →</a></p>
    <p><a href="{{ url_for('bills') }}">View Bill History →</a></p>
    <p><a href="{{ url_for('customers') }}">Manage Customers →</a></p>
    <p><a href="{{ url_for('products') }}">Manage Products →</a></p>
</section>
{% endblock %}
""",
}

app.jinja_loader = DictLoader(TEMPLATES)


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    connection = sqlite3.connect(app.config["DATABASE"], timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db() -> None:
    with get_db() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                price REAL NOT NULL,
                stock REAL NOT NULL,
                unit TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS bills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created TEXT NOT NULL,
                customer TEXT NOT NULL DEFAULT '',
                subtotal REAL NOT NULL,
                discount REAL NOT NULL,
                discount_pct REAL NOT NULL DEFAULT 0,
                tax REAL NOT NULL,
                total REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS bill_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_id INTEGER NOT NULL REFERENCES bills(id),
                name TEXT NOT NULL,
                price REAL NOT NULL,
                qty REAL NOT NULL,
                unit TEXT NOT NULL,
                line_total REAL NOT NULL
            );
            """
        )
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL DEFAULT '',
                created TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_id INTEGER NOT NULL REFERENCES bills(id),
                customer_id INTEGER NOT NULL REFERENCES customers(id),
                amount REAL NOT NULL CHECK (amount > 0),
                method TEXT NOT NULL DEFAULT 'Cash',
                created TEXT NOT NULL
            );
            """
        )

        columns = {
            row["name"]
            for row in db.execute("PRAGMA table_info(bills)")
        }

        if "discount_pct" not in columns:
            db.execute(
                "ALTER TABLE bills ADD COLUMN "
                "discount_pct REAL NOT NULL DEFAULT 0"
            )

        if "customer_id" not in columns:
            db.execute(
                "ALTER TABLE bills ADD COLUMN "
                "customer_id INTEGER REFERENCES customers(id)"
            )

        if "paid_amount" not in columns:
            db.execute(
                "ALTER TABLE bills ADD COLUMN "
                "paid_amount REAL NOT NULL DEFAULT 0"
            )
        product_count = db.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if product_count == 0:
            db.executemany(
                "INSERT INTO products (name, price, stock, unit) VALUES (?, ?, ?, ?)",
                SAMPLE_PRODUCTS,
            )


def decimal_value(value: Any, label: str) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{label} must be a valid number.")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{label} must be a valid number.") from None
    if not number.is_finite():
        raise ValueError(f"{label} must be a valid number.")
    return number


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_totals(subtotal: Decimal) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    discount_pct = Decimal("0")
    for minimum, percentage in DISCOUNT_TIERS:
        if subtotal >= Decimal(str(minimum)):
            discount_pct = Decimal(str(percentage))
            break
    discount = money(subtotal * discount_pct / Decimal("100"))
    tax = money((subtotal - discount) * Decimal(str(TAX_RATE)) / Decimal("100"))
    total = money(subtotal - discount + tax)
    return discount, discount_pct, tax, total


def template_context() -> dict[str, Any]:
    return {
        "store_name": STORE_NAME,
        "store_address": STORE_ADDRESS,
        "currency": CURRENCY,
        "tax_rate": TAX_RATE,
        "discount_tiers": DISCOUNT_TIERS,
    }


@app.get("/")
def index():
    with get_db() as db:
        products = db.execute(
            """
            SELECT id, name, price, stock, unit
            FROM products
            WHERE stock > 0
            ORDER BY name
            """
        ).fetchall()

        customers = db.execute(
            "SELECT id, name, phone FROM customers ORDER BY name"
        ).fetchall()

    return render_template(
        "billing.html",
        products=[dict(product) for product in products],
        customers=[dict(customer) for customer in customers],
        **template_context(),
    )

("/api/bills")
@app.post("/api/bills")
def api_create_bill():
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return jsonify(error="Request body must be a JSON object."), 400

    items = payload.get("items")
    if not isinstance(items, list) or not items:
        return jsonify(error="Add at least one product to the cart."), 400

    customer = payload.get("customer", "")
    if not isinstance(customer, str):
        return jsonify(error="Customer name must be text."), 400

    customer = customer.strip()[:120]
    customer_id = payload.get("customer_id")
    payment_method = payload.get("payment_method", "Cash")

    if payment_method not in ("Cash", "UPI", "Card"):
        return jsonify(error="Invalid payment method."), 400

    try:
        if customer_id in ("", None):
            customer_id = None
        else:
            if isinstance(customer_id, bool):
                raise ValueError("Invalid registered customer.")
            customer_id = int(customer_id)
            if customer_id <= 0:
                raise ValueError("Invalid registered customer.")

        requested: dict[int, Decimal] = {}

        for item in items:
            if not isinstance(item, dict):
                raise ValueError("Each cart item must be an object.")

            product_id = item.get("product_id")
            if isinstance(product_id, bool):
                raise ValueError("Invalid product.")

            try:
                product_id = int(product_id)
            except (TypeError, ValueError):
                raise ValueError("Invalid product.") from None

            qty = decimal_value(item.get("qty"), "Quantity")
            if qty <= 0:
                raise ValueError("Quantity must be greater than zero.")

            requested[product_id] = (
                requested.get(product_id, Decimal("0")) + qty
            )

        with get_db() as db:
            db.execute("BEGIN IMMEDIATE")

            registered_customer = None

            if customer_id is not None:
                registered_customer = db.execute(
                    "SELECT id, name FROM customers WHERE id = ?",
                    (customer_id,),
                ).fetchone()

                if registered_customer is None:
                    raise ValueError("Registered customer not found.")

                customer = registered_customer["name"]

            ids = list(requested)
            placeholders = ",".join("?" for _ in ids)

            rows = db.execute(
                f"""
                SELECT id, name, price, stock, unit
                FROM products
                WHERE id IN ({placeholders})
                """,
                ids,
            ).fetchall()

            products_by_id = {row["id"]: row for row in rows}

            if any(pid not in products_by_id for pid in requested):
                raise ValueError(
                    "One or more selected products no longer exist."
                )

            line_items = []
            subtotal = Decimal("0")

            for product_id, qty in requested.items():
                product = products_by_id[product_id]

                if qty > Decimal(str(product["stock"])):
                    raise ValueError(
                        f"Only {product['stock']:g} "
                        f"{product['unit']} of {product['name']} are available."
                    )

                price = money(Decimal(str(product["price"])))
                line_total = money(price * qty)
                subtotal += line_total

                line_items.append({
                    "id": product_id,
                    "name": product["name"],
                    "price": price,
                    "qty": qty,
                    "unit": product["unit"],
                    "line_total": line_total,
                })

            subtotal = money(subtotal)
            discount, discount_pct, tax, total = calculate_totals(subtotal)

            paid_input = payload.get("paid_amount", None)

            if paid_input is None:
                paid_amount = total
            else:
                paid_amount = money(
                    decimal_value(paid_input, "Amount paid")
                )

            if paid_amount < 0:
                raise ValueError("Amount paid cannot be negative.")

            if paid_amount > total:
                raise ValueError(
                    "Amount paid cannot exceed the bill total."
                )

            if paid_amount < total and customer_id is None:
                raise ValueError(
                    "Select a registered customer to record Udhar."
                )

            balance_due = money(total - paid_amount)

            cursor = db.execute(
                """
                INSERT INTO bills
                    (
                        created, customer, customer_id,
                        subtotal, discount, discount_pct,
                        tax, total, paid_amount
                    )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    customer,
                    customer_id,
                    float(subtotal),
                    float(discount),
                    float(discount_pct),
                    float(tax),
                    float(total),
                    float(paid_amount),
                ),
            )

            bill_id = cursor.lastrowid

            for item in line_items:
                db.execute(
                    """
                    INSERT INTO bill_items
                        (bill_id, name, price, qty, unit, line_total)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        bill_id,
                        item["name"],
                        float(item["price"]),
                        float(item["qty"]),
                        item["unit"],
                        float(item["line_total"]),
                    ),
                )

                db.execute(
                    "UPDATE products SET stock = stock - ? WHERE id = ?",
                    (float(item["qty"]), item["id"]),
                )

            if customer_id is not None and paid_amount > 0:
                db.execute(
                    """
                    INSERT INTO payments
                        (bill_id, customer_id, amount, method, created)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        bill_id,
                        customer_id,
                        float(paid_amount),
                        payment_method,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )

    except (ValueError, TypeError, InvalidOperation) as error:
        return jsonify(error=str(error)), 400
    except Exception:
        app.logger.exception("Failed to save bill")
        return jsonify(
            error="The bill could not be saved. Please check the database setup."
        ), 500

    return jsonify(
        redirect=url_for("invoice", bill_id=bill_id),
        total=float(total),
        paid=float(paid_amount),
        balance_due=float(balance_due),
    ), 201


@app.get("/bill/<int:bill_id>")
def invoice(bill_id: int):
    with get_db() as db:
        bill = db.execute("SELECT * FROM bills WHERE id = ?", (bill_id,)).fetchone()
        if bill is None:
            return "Bill not found", 404
        items = db.execute(
            "SELECT name, price, qty, unit, line_total FROM bill_items WHERE bill_id = ? ORDER BY id",
            (bill_id,),
        ).fetchall()
    return render_template("invoice.html", bill=bill, items=items, **template_context())


@app.get("/bills")
def bills():
    today = date.today().isoformat()
    with get_db() as db:
        recent = db.execute(
            "SELECT * FROM bills ORDER BY id DESC LIMIT 200"
        ).fetchall()
        summary = db.execute(
            """SELECT COUNT(*) AS count, COALESCE(SUM(total), 0) AS sales
               FROM bills WHERE substr(created, 1, 10) = ?""",
            (today,),
        ).fetchone()
    return render_template(
        "bills.html",
        bills=recent,
        today_count=summary["count"],
        today_sales=summary["sales"],
        **template_context(),
    )


def product_form_values(form: Any) -> tuple[str, float, int, str]:
    name = form.get("name", "").strip()
    unit = form.get("unit", "").strip()
    if not name or len(name) > 100:
        raise ValueError("Product name is required and must be 100 characters or fewer.")
    if not unit or len(unit) > 20:
        raise ValueError("Unit is required and must be 20 characters or fewer.")
    price = decimal_value(form.get("price"), "Price")
    stock = decimal_value(form.get("stock"), "Stock")
    if price < 0:
        raise ValueError("Price cannot be negative.")
    if stock < 0:
        raise ValueError("Stock must be greater than or equal to zero.")
    return name, float(money(price)), float(stock), unit


@app.get("/products")
def products():
    with get_db() as db:
        inventory = db.execute(
            "SELECT id, name, price, stock, unit FROM products ORDER BY name"
        ).fetchall()
    return render_template("products.html", products=inventory, **template_context())


@app.post("/products/add")
def add_product():
    try:
        values = product_form_values(request.form)
        with get_db() as db:
            db.execute(
                "INSERT INTO products (name, price, stock, unit) VALUES (?, ?, ?, ?)",
                values,
            )
        flash(f"{values[0]} added to inventory.")
    except ValueError as error:
        flash(str(error), "error")
    except sqlite3.IntegrityError:
        flash("A product with that name already exists.", "error")
    return redirect(url_for("products"))


@app.post("/products/<int:product_id>/update")
def update_product(product_id: int):
    try:
        values = product_form_values(request.form)
        with get_db() as db:
            cursor = db.execute(
                "UPDATE products SET name = ?, price = ?, stock = ?, unit = ? WHERE id = ?",
                (*values, product_id),
            )
            if cursor.rowcount == 0:
                flash("Product not found.", "error")
            else:
                flash(f"{values[0]} updated.")
    except ValueError as error:
        flash(str(error), "error")
    except sqlite3.IntegrityError:
        flash("A product with that name already exists.", "error")
    return redirect(url_for("products"))


@app.post("/products/<int:product_id>/delete")
def delete_product(product_id: int):
    with get_db() as db:
        cursor = db.execute("DELETE FROM products WHERE id = ?", (product_id,))
    flash("Product deleted." if cursor.rowcount else "Product not found.", "error" if not cursor.rowcount else "message")
    return redirect(url_for("products"))


with app.app_context():
    init_db()

@app.route("/customers")
def customers():
    with get_db() as db:
        rows = db.execute(
            """
            SELECT
                c.id,
                c.name,
                c.phone,
                COALESCE(
                    SUM(b.total - b.paid_amount), 0
                ) AS balance
            FROM customers c
            LEFT JOIN bills b
                ON b.customer_id = c.id
            GROUP BY c.id, c.name, c.phone
            ORDER BY c.name
            """
        ).fetchall()

    return render_template(
        "customers.html",
        customers=rows,
        **template_context()
    )


@app.route("/customers/add", methods=["POST"])
def add_customer():
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()

    if not name:
        flash("Please enter a customer name.", "error")
        return redirect(url_for("customers"))

    with get_db() as db:
        db.execute(
            """
            INSERT INTO customers (name, phone, created)
            VALUES (?, ?, ?)
            """,
            (
                name,
                phone,
                datetime.now().isoformat(timespec="seconds")
            )
        )

    flash("Customer added successfully.", "success")
    return redirect(url_for("customers"))
@app.route("/customers/<int:customer_id>/pay", methods=["POST"])
def collect_udhar(customer_id):
    amount_text = request.form.get("amount", "").strip()
    payment_method = request.form.get("payment_method", "Cash")

    if payment_method not in ("Cash", "UPI", "Card"):
        flash("Invalid payment method.", "error")
        return redirect(url_for("customers"))

    try:
        amount = money(decimal_value(amount_text, "Payment amount"))

        if amount <= 0:
            raise ValueError("Payment must be greater than zero.")

        with get_db() as db:
            db.execute("BEGIN IMMEDIATE")

            customer = db.execute(
                "SELECT id, name FROM customers WHERE id = ?",
                (customer_id,),
            ).fetchone()

            if customer is None:
                raise ValueError("Customer not found.")

            outstanding = db.execute(
                """
                SELECT COALESCE(SUM(total - paid_amount), 0) AS balance
                FROM bills
                WHERE customer_id = ?
                """,
                (customer_id,),
            ).fetchone()["balance"]

            outstanding = money(Decimal(str(outstanding)))

            if outstanding <= 0:
                raise ValueError("This customer has no outstanding Udhar.")

            if amount > outstanding:
                raise ValueError(
                    f"Payment cannot exceed the outstanding balance of ₹{outstanding:.2f}."
                )

            remaining_payment = amount

            unpaid_bills = db.execute(
                """
                SELECT id, total, paid_amount
                FROM bills
                WHERE customer_id = ?
                  AND paid_amount < total
                ORDER BY created ASC, id ASC
                """,
                (customer_id,),
            ).fetchall()

            for bill in unpaid_bills:
                if remaining_payment <= 0:
                    break

                bill_due = money(
                    Decimal(str(bill["total"]))
                    - Decimal(str(bill["paid_amount"]))
                )

                applied = min(remaining_payment, bill_due)
                new_paid_amount = money(
                    Decimal(str(bill["paid_amount"])) + applied
                )

                db.execute(
                    "UPDATE bills SET paid_amount = ? WHERE id = ?",
                    (float(new_paid_amount), bill["id"]),
                )

                db.execute(
                    """
                    INSERT INTO payments
                        (bill_id, customer_id, amount, method, created)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        bill["id"],
                        customer_id,
                        float(applied),
                        payment_method,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )

                remaining_payment = money(remaining_payment - applied)

        flash(
            f"₹{amount:.2f} collected from {customer['name']} successfully.",
            "success",
        )

    except (ValueError, TypeError, InvalidOperation) as error:
        flash(str(error), "error")

    except Exception:
        app.logger.exception("Failed to collect Udhar payment")
        flash("Payment could not be recorded. Please try again.", "error")

    return redirect(url_for("customers"))
@app.route("/customers/<int:customer_id>/ledger")
def customer_ledger(customer_id):
    with get_db() as db:
        customer = db.execute(
            """
            SELECT id, name, phone
            FROM customers
            WHERE id = ?
            """,
            (customer_id,),
        ).fetchone()

        if customer is None:
            flash("Customer not found.", "error")
            return redirect(url_for("customers"))

        bills = db.execute(
            """
            SELECT
                id,
                created,
                total,
                paid_amount,
                total - paid_amount AS balance_due
            FROM bills
            WHERE customer_id = ?
            ORDER BY created DESC, id DESC
            """,
            (customer_id,),
        ).fetchall()

        payments = db.execute(
            """
            SELECT
                p.amount,
                p.method,
                p.created,
                p.bill_id
            FROM payments p
            WHERE p.customer_id = ?
            ORDER BY p.created DESC, p.id DESC
            """,
            (customer_id,),
        ).fetchall()

        balance = db.execute(
            """
            SELECT COALESCE(SUM(total - paid_amount), 0) AS balance
            FROM bills
            WHERE customer_id = ?
            """,
            (customer_id,),
        ).fetchone()["balance"]

    return render_template(
        "ledger.html",
        customer=dict(customer),
        bills=[dict(bill) for bill in bills],
        payments=[dict(payment) for payment in payments],
        balance=balance,
        **template_context(),
    )
@app.route("/reports")
def sales_report():
    today = date.today().isoformat()

    with get_db() as db:
        summary = db.execute(
            """
            SELECT
                COUNT(*) AS bill_count,
                COALESCE(SUM(total), 0) AS total_sales,
                COALESCE(SUM(paid_amount), 0) AS amount_collected,
                COALESCE(SUM(total - paid_amount), 0) AS udhar_added
            FROM bills
            WHERE substr(created, 1, 10) = ?
            """,
            (today,),
        ).fetchone()

        top_products = db.execute(
            """
            SELECT
                bi.name,
                SUM(bi.qty) AS quantity_sold,
                SUM(bi.line_total) AS sales_amount
            FROM bill_items bi
            JOIN bills b ON b.id = bi.bill_id
            WHERE substr(b.created, 1, 10) = ?
            GROUP BY bi.name
            ORDER BY quantity_sold DESC, sales_amount DESC
            LIMIT 5
            """,
            (today,),
        ).fetchall()

    return render_template(
        "reports.html",
        report_date=today,
        summary=dict(summary),
        top_products=[dict(product) for product in top_products],
        **template_context(),
    )
if __name__ == "__main__":
    app.run(debug=True)
