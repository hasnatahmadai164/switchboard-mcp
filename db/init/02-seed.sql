
INSERT INTO customers (name, email) VALUES
    ('Amara Okafor', 'amara.okafor@example.com'),
    ('Liam Chen', 'liam.chen@example.com'),
    ('Priya Nair', 'priya.nair@example.com')
ON CONFLICT (email) DO NOTHING;

INSERT INTO orders (customer_id, item, quantity, total_cents, status) VALUES
    (1, 'Wireless Mouse', 2, 4998, 'shipped'),
    (1, 'USB-C Hub', 1, 3499, 'pending'),
    (2, 'Mechanical Keyboard', 1, 8999, 'shipped'),
    (3, 'Monitor Stand', 1, 2999, 'delivered');
