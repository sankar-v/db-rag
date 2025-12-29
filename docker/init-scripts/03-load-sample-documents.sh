#!/bin/bash
set -e

echo "========================================"
echo "Loading sample documents"
echo "========================================"

psql -U postgres -d pagila <<-EOSQL
    -- Insert sample company documents for testing vector search

    -- Sample policy documents
    INSERT INTO company_documents (content, metadata) VALUES 
    (
        'DVD Rental Policy: Customers can rent DVDs for up to 7 days. Late fees are \$1.50 per day. Customers must have a valid membership card. Maximum of 5 rentals at a time. New releases have a 3-day rental period.',
        '{"type": "policy", "department": "rental", "category": "customer_service"}'::jsonb
    ),
    (
        'Membership Policy: Annual membership costs \$25. Members receive 10% discount on all rentals. Birthday month special: rent 3 get 1 free. Membership can be renewed online or in-store. Student discount available with valid ID.',
        '{"type": "policy", "department": "membership", "category": "customer_service"}'::jsonb
    ),
    (
        'Refund and Return Policy: Damaged DVDs can be returned within 24 hours for full refund. Customer must report damage immediately. No refunds after 24 hours. Exchange available for defective items within rental period.',
        '{"type": "policy", "department": "customer_service", "category": "returns"}'::jsonb
    ),
    (
        'Staff Guidelines: All staff must greet customers within 30 seconds. Process rentals efficiently. Verify customer ID for new memberships. Maintain cleanliness of store. Report inventory issues to manager immediately.',
        '{"type": "handbook", "department": "operations", "category": "staff"}'::jsonb
    ),
    (
        'Inventory Management: New releases are stocked based on demand forecasts. Maintain minimum 3 copies of popular titles. Weekly inventory audits required. Damaged items must be documented and removed from circulation.',
        '{"type": "procedure", "department": "inventory", "category": "operations"}'::jsonb
    ),
    (
        'Payment Policy: We accept cash, credit cards, and debit cards. Online payments accepted through secure portal. Late fees can be waived once per year at manager discretion. Payment plans available for accounts over \$50.',
        '{"type": "policy", "department": "finance", "category": "payments"}'::jsonb
    ),
    (
        'Customer Privacy Policy: Customer data is protected and encrypted. Personal information is not shared with third parties. Customers can request data deletion at any time. Rental history is kept for 2 years for recommendations.',
        '{"type": "policy", "department": "legal", "category": "privacy"}'::jsonb
    );

    SELECT COUNT(*) as documents_loaded FROM company_documents;

EOSQL

echo "Sample documents loaded successfully!"
