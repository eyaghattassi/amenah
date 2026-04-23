
CREATE TABLE IF NOT EXISTS waiting (
    id INT NOT NULL AUTO_INCREMENT,
    nom VARCHAR(500) NOT NULL,
    categorie VARCHAR(100) NULL,
    description TEXT NULL,
    lien_source VARCHAR(2000) NULL,
    email_contact VARCHAR(320) NULL,
    created_at VARCHAR(64) NOT NULL,
    statut VARCHAR(32) NOT NULL DEFAULT 'en_attente',
    suggestion_type VARCHAR(16) NOT NULL DEFAULT 'boycott',
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS produits (
    id INT NOT NULL AUTO_INCREMENT,
    nom VARCHAR(500) NOT NULL,
    categorie VARCHAR(100) NULL,
    description TEXT NULL,
    lien_source VARCHAR(2000) NULL,
    accepted_from_waiting_id INT NULL,
    created_at VARCHAR(64) NOT NULL,
    code_barre VARCHAR(16) NULL,
    PRIMARY KEY (id),
    UNIQUE KEY idx_produits_nom_categorie (nom(255), categorie(100))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS feedback (
    id INT NOT NULL AUTO_INCREMENT,
    message TEXT NOT NULL,
    created_at VARCHAR(64) NOT NULL,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS produit_alternatives (
    id INT NOT NULL AUTO_INCREMENT,
    nom VARCHAR(500) NOT NULL,
    categorie VARCHAR(100) NULL,
    description TEXT NULL,
    lien_source VARCHAR(2000) NULL,
    created_at VARCHAR(64) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY idx_produit_alternatives_nom_categorie (nom(255), categorie(100))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO produits (nom, categorie, description, lien_source, accepted_from_waiting_id, created_at) VALUES
('Coca Cola', 'food', NULL, NULL, NULL, NOW()),
('Cheetos', 'food', NULL, NULL, NULL, NOW()),
('Adidas', 'clothing', NULL, NULL, NULL, NOW()),
('Apple', 'tech', NULL, NULL, NULL, NOW()),
('BBC', 'media', NULL, NULL, NULL, NOW()),
('Bioderma', 'cleaning', NULL, NULL, NULL, NOW()),
('Blackrock', 'finance', NULL, NULL, NULL, NOW()),
('CNN', 'media', NULL, NULL, NULL, NOW()),
('Colgate', 'cleaning', NULL, NULL, NULL, NOW()),
('Dell', 'tech', NULL, NULL, NULL, NOW()),
('Danone', 'food', NULL, NULL, NULL, NOW()),
('Disney', 'media', NULL, NULL, NULL, NOW()),
('Doritos', 'food', NULL, NULL, NULL, NOW()),
('Dove', 'cleaning', NULL, NULL, NULL, NOW()),
('Fanta', 'food', NULL, NULL, NULL, NOW()),
('Garnier', 'cleaning', NULL, NULL, NULL, NOW()),
('Gillette', 'cleaning', NULL, NULL, NULL, NOW()),
('Google', 'media', NULL, NULL, NULL, NOW()),
('Head & Shoulders', 'cleaning', NULL, NULL, NULL, NOW()),
('HP', 'tech', NULL, NULL, NULL, NOW()),
('IBM', 'tech', NULL, NULL, NULL, NOW()),
('Intel', 'tech', NULL, NULL, NULL, NOW()),
('JP Morgan', 'finance', NULL, NULL, NULL, NOW()),
('Lays', 'food', NULL, NULL, NULL, NOW()),
('La Roche Posay', 'cleaning', NULL, NULL, NULL, NOW()),
('Lipton', 'food', NULL, NULL, NULL, NOW()),
('L''Oreal', 'cleaning', NULL, NULL, NULL, NOW()),
('MAC', 'cleaning', NULL, NULL, NULL, NOW()),
('Louis Vuitton', 'clothing', NULL, NULL, NULL, NOW()),
('Mars', 'food', NULL, NULL, NULL, NOW()),
('Mastercard', 'finance', NULL, NULL, NULL, NOW()),
('Meta', 'media', NULL, NULL, NULL, NOW()),
('Microsoft', 'tech', NULL, NULL, NULL, NOW()),
('Netflix', 'media', NULL, NULL, NULL, NOW()),
('Nestle', 'food', NULL, NULL, NULL, NOW()),
('New York Times', 'media', NULL, NULL, NULL, NOW()),
('Nike', 'clothing', NULL, NULL, NULL, NOW()),
('Nivea', 'cleaning', NULL, NULL, NULL, NOW()),
('Nvidia', 'tech', NULL, NULL, NULL, NOW()),
('Oreo', 'food', NULL, NULL, NULL, NOW()),
('Paypal', 'finance', NULL, NULL, NULL, NOW()),
('Pepsi', 'food', NULL, NULL, NULL, NOW()),
('President', 'food', NULL, NULL, NULL, NOW()),
('Puma', 'clothing', NULL, NULL, NULL, NOW()),
('Reebok', 'clothing', NULL, NULL, NULL, NOW()),
('Snickers', 'food', NULL, NULL, NULL, NOW()),
('Sephora', 'cleaning', NULL, NULL, NULL, NOW()),
('Signal', 'cleaning', NULL, NULL, NULL, NOW()),
('Starbucks', 'food', NULL, NULL, NULL, NOW()),
('Vasline', 'cleaning', NULL, NULL, NULL, NOW()),
('Veet', 'cleaning', NULL, NULL, NULL, NOW()),
('Visa', 'finance', NULL, NULL, NULL, NOW()),
('Zara', 'clothing', NULL, NULL, NULL, NOW());


UPDATE produits SET code_barre = '5449000211916' WHERE nom = 'Coca Cola';
UPDATE produits SET code_barre = '5900000000001' WHERE nom = 'Cheetos';
UPDATE produits SET code_barre = '5900000000002' WHERE nom = 'Adidas';
UPDATE produits SET code_barre = '5900000000003' WHERE nom = 'Apple';
UPDATE produits SET code_barre = '5900000000004' WHERE nom = 'BBC';
UPDATE produits SET code_barre = '5900000000005' WHERE nom = 'Bioderma';
UPDATE produits SET code_barre = '5900000000006' WHERE nom = 'Blackrock';
UPDATE produits SET code_barre = '5900000000007' WHERE nom = 'CNN';
UPDATE produits SET code_barre = '5900000000008' WHERE nom = 'Colgate';
UPDATE produits SET code_barre = '5900000000009' WHERE nom = 'Dell';
UPDATE produits SET code_barre = '3760055570239' WHERE nom = 'Danone';
UPDATE produits SET code_barre = '5900000000010' WHERE nom = 'Disney';
UPDATE produits SET code_barre = '5900000000011' WHERE nom = 'Doritos';
UPDATE produits SET code_barre = '5900000000012' WHERE nom = 'Dove';
UPDATE produits SET code_barre = '5449000211918' WHERE nom = 'Fanta';
UPDATE produits SET code_barre = '3600540004321' WHERE nom = 'Garnier';
UPDATE produits SET code_barre = '5900000000013' WHERE nom = 'Gillette';
UPDATE produits SET code_barre = '5900000000014' WHERE nom = 'Google';
UPDATE produits SET code_barre = '5900000000015' WHERE nom = 'Head & Shoulders';
UPDATE produits SET code_barre = '8859098012345' WHERE nom = 'HP';
UPDATE produits SET code_barre = '5900000000016' WHERE nom = 'IBM';
UPDATE produits SET code_barre = '5900000000017' WHERE nom = 'Intel';
UPDATE produits SET code_barre = '5900000000018' WHERE nom = 'JP Morgan';
UPDATE produits SET code_barre = '5410124114418' WHERE nom = 'Lays';
UPDATE produits SET code_barre = '5900000000019' WHERE nom = 'La Roche Posay';
UPDATE produits SET code_barre = '5900000000020' WHERE nom = 'Lipton';
UPDATE produits SET code_barre = '3245410008765' WHERE nom = 'L''Oreal';
UPDATE produits SET code_barre = '5900000000021' WHERE nom = 'MAC';
UPDATE produits SET code_barre = '5900000000022' WHERE nom = 'Louis Vuitton';
UPDATE produits SET code_barre = '5900000000023' WHERE nom = 'Mars';
UPDATE produits SET code_barre = '5900000000024' WHERE nom = 'Mastercard';
UPDATE produits SET code_barre = '5900000000025' WHERE nom = 'Meta';
UPDATE produits SET code_barre = '5900000000026' WHERE nom = 'Microsoft';
UPDATE produits SET code_barre = '5900000000027' WHERE nom = 'Netflix';
UPDATE produits SET code_barre = '5000112543261' WHERE nom = 'Nestle';
UPDATE produits SET code_barre = '5900000000028' WHERE nom = 'New York Times';
UPDATE produits SET code_barre = '5900000000029' WHERE nom = 'Nike';
UPDATE produits SET code_barre = '5900000000030' WHERE nom = 'Nivea';
UPDATE produits SET code_barre = '5900000000031' WHERE nom = 'Nvidia';
UPDATE produits SET code_barre = '5000159421874' WHERE nom = 'Oreo';
UPDATE produits SET code_barre = '5900000000032' WHERE nom = 'Paypal';
UPDATE produits SET code_barre = '7622210447283' WHERE nom = 'Pepsi';
UPDATE produits SET code_barre = '5900000000033' WHERE nom = 'President';
UPDATE produits SET code_barre = '5900000000034' WHERE nom = 'Puma';
UPDATE produits SET code_barre = '5900000000035' WHERE nom = 'Reebok';
UPDATE produits SET code_barre = '5900000000036' WHERE nom = 'Snickers';
UPDATE produits SET code_barre = '5900000000037' WHERE nom = 'Sephora';
UPDATE produits SET code_barre = '5900000000038' WHERE nom = 'Signal';
UPDATE produits SET code_barre = '7622210588016' WHERE nom = 'Starbucks';
UPDATE produits SET code_barre = '5900000000039' WHERE nom = 'Vasline';
UPDATE produits SET code_barre = '5900000000040' WHERE nom = 'Veet';
UPDATE produits SET code_barre = '5900000000041' WHERE nom = 'Visa';
UPDATE produits SET code_barre = '5900000000042' WHERE nom = 'Zara';

INSERT IGNORE INTO produit_alternatives (nom, categorie, description, lien_source, created_at) VALUES
('Zamzam Cola', 'food', 'Cola from Saudi Arabia; often chosen as a non–Western soft drink option.', NULL, NOW()),
('Mecca Cola', 'food', '“Ethical cola” brand launched as an alternative to major global soda labels.', NULL, NOW()),
('Water / Homemade', 'food', 'Simplest drink: water, or homemade juices and infusions without excess sugar.', NULL, NOW()),
('Local Cafés & Restaurants', 'food', 'Prefer independent venues to support your local economy and reduce chain dependency.', NULL, NOW()),
('make it at home', 'food', 'Cooking and baking at home: you control ingredients, cost, and waste.', NULL, NOW()),
('DuckDuckGo', 'tech', 'Search engine focused on privacy: no personalized ad profiles by default.', NULL, NOW()),
('ecosia', 'tech', 'Uses ad revenue to fund tree planting; transparent reports on supported projects.', NULL, NOW()),
('local shops', 'tech', 'Buy electronics and gear from local retailers when possible—easier support and repairs.', NULL, NOW()),
('jumia', 'tech', 'Major African e-commerce platform; useful where global marketplaces have less coverage.', NULL, NOW()),
('AMD processors', 'tech', 'CPU/GPU alternative to the dominant x86 vendor; strong value in many segments.', NULL, NOW()),
('new balance', 'clothing', 'Footwear and apparel brand; often cited for wider sizing and some domestic manufacturing.', NULL, NOW()),
('local brands', 'clothing', 'Smaller labels and regional makers—often more traceable than fast fashion giants.', NULL, NOW()),
('secand_hand/thrift', 'clothing', 'Second-hand and thrift: reuse, lower footprint, and unique finds.', NULL, NOW()),
('mastodon', 'media', 'Federated social network: many independent servers, no single company owns the whole network.', NULL, NOW()),
('telegram', 'media', 'Cloud-based messenger with channels and large groups; check privacy settings for your use case.', NULL, NOW()),
('tiktok(with caution)', 'media', 'Short video app: be mindful of screen time, data policy, and age-appropriate content.', NULL, NOW()),
('local cosmetics brands', 'cleaning', 'Regional producers often offer simpler formulas and less global shipping.', NULL, NOW()),
('lush cosmetics', 'cleaning', 'Handmade-style cosmetics with visible sourcing; check ingredients if you have sensitivities.', NULL, NOW()),
('DIY natura cleaning', 'cleaning', 'Vinegar, baking soda, and plant-based recipes—cheap and fewer harsh chemicals.', NULL, NOW());

UPDATE produit_alternatives SET description = 'Cola from Saudi Arabia; often chosen as a non–Western soft drink option.' WHERE nom = 'Zamzam Cola' AND description IS NULL;
UPDATE produit_alternatives SET description = '“Ethical cola” brand launched as an alternative to major global soda labels.' WHERE nom = 'Mecca Cola' AND description IS NULL;
UPDATE produit_alternatives SET description = 'Simplest drink: water, or homemade juices and infusions without excess sugar.' WHERE nom = 'Water / Homemade' AND description IS NULL;
UPDATE produit_alternatives SET description = 'Prefer independent venues to support your local economy and reduce chain dependency.' WHERE nom = 'Local Cafés & Restaurants' AND description IS NULL;
UPDATE produit_alternatives SET description = 'Cooking and baking at home: you control ingredients, cost, and waste.' WHERE nom = 'make it at home' AND description IS NULL;
UPDATE produit_alternatives SET description = 'Search engine focused on privacy: no personalized ad profiles by default.' WHERE nom = 'DuckDuckGo' AND description IS NULL;
UPDATE produit_alternatives SET description = 'Uses ad revenue to fund tree planting; transparent reports on supported projects.' WHERE nom = 'ecosia' AND description IS NULL;
UPDATE produit_alternatives SET description = 'Buy electronics and gear from local retailers when possible—easier support and repairs.' WHERE nom = 'local shops' AND description IS NULL;
UPDATE produit_alternatives SET description = 'Major African e-commerce platform; useful where global marketplaces have less coverage.' WHERE nom = 'jumia' AND description IS NULL;
UPDATE produit_alternatives SET description = 'CPU/GPU alternative to the dominant x86 vendor; strong value in many segments.' WHERE nom = 'AMD processors' AND description IS NULL;
UPDATE produit_alternatives SET description = 'Footwear and apparel brand; often cited for wider sizing and some domestic manufacturing.' WHERE nom = 'new balance' AND description IS NULL;
UPDATE produit_alternatives SET description = 'Smaller labels and regional makers—often more traceable than fast fashion giants.' WHERE nom = 'local brands' AND description IS NULL;
UPDATE produit_alternatives SET description = 'Second-hand and thrift: reuse, lower footprint, and unique finds.' WHERE nom = 'secand_hand/thrift' AND description IS NULL;
UPDATE produit_alternatives SET description = 'Federated social network: many independent servers, no single company owns the whole network.' WHERE nom = 'mastodon' AND description IS NULL;
UPDATE produit_alternatives SET description = 'Cloud-based messenger with channels and large groups; check privacy settings for your use case.' WHERE nom = 'telegram' AND description IS NULL;
UPDATE produit_alternatives SET description = 'Short video app: be mindful of screen time, data policy, and age-appropriate content.' WHERE nom = 'tiktok(with caution)' AND description IS NULL;
UPDATE produit_alternatives SET description = 'Regional producers often offer simpler formulas and less global shipping.' WHERE nom = 'local cosmetics brands' AND description IS NULL;
UPDATE produit_alternatives SET description = 'Handmade-style cosmetics with visible sourcing; check ingredients if you have sensitivities.' WHERE nom = 'lush cosmetics' AND description IS NULL;
UPDATE produit_alternatives SET description = 'Vinegar, baking soda, and plant-based recipes—cheap and fewer harsh chemicals.' WHERE nom = 'DIY natura cleaning' AND description IS NULL;


CREATE TABLE IF NOT EXISTS donation_agencies (
    id INT NOT NULL AUTO_INCREMENT,
    slug VARCHAR(64) NOT NULL,
    name VARCHAR(500) NOT NULL,
    card_summary TEXT NOT NULL,
    body_text TEXT NOT NULL,
    hero_image_url VARCHAR(2000) NULL,
    logo_url VARCHAR(2000) NULL,
    gallery_json TEXT NOT NULL,
    donate_url VARCHAR(2000) NOT NULL,
    sort_order INT NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY idx_donation_agencies_slug (slug)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO donation_agencies (slug, name, card_summary, body_text, hero_image_url, logo_url, gallery_json, donate_url, sort_order) VALUES
('wfp', 'Programme alimentaire mondial (PAM / WFP)', 'Nations Unies — appel Palestine : aide alimentaire d’urgence et soutien aux familles.', 'Le Programme alimentaire mondial (PAM / WFP) est l’agence humanitaire de l’ONU chargée de lutter contre la faim. En Palestine, le PAM distribue des vivres d’urgence, soutient les boulangeries et lutte contre la malnutrition chez les enfants et les femmes enceintes ou allaitantes.\n\nAprès des années de conflit et de déplacements massifs, des centaines de milliers de familles dépendent de l’aide alimentaire. Les dons financent des colis prêts à consommer, des compléments nutritionnels et de la farine pour le pain.\n\nChaque contribution aide à atteindre les personnes les plus vulnérables : enfants, personnes âgées, mères isolées, personnes en situation de handicap.', 'https://www.wfp.org/sites/default/files/styles/open_graph_image/public/images/Ali1%20%281%29_2.jpg?itok=nWijx07N', 'static/donations/wfp.svg', '[]', 'https://www.wfp.org/support-us/stories/palestine-appeal', 1),
('solidarites', 'Solidarités International', 'ONG française — missions eau, assainissement et urgence en Palestine et bande de Gaza.', 'Solidarités International est une ONG française d’aide humanitaire spécialisée dans l’eau, l’assainissement et la sécurité alimentaire.\n\nEn Palestine et dans la bande de Gaza, l’équipe intervient pour rétablir l’accès à l’eau potable, prévenir les épidémies et soutenir les ménages en situation d’urgence.\n\nLes dons financent des programmes concrets : infrastructures, hygiène et accompagnement des populations les plus exposées.', 'https://www.solidarites.org/wp-content/uploads/2024/06/carte-bande-de-gaza-palestine.jpg', 'static/donations/solidarites.svg', '["https://www.solidarites.org/wp-content/uploads/2023/12/Philippe_Bonnet-1.jpg"]', 'https://www.solidarites.org/fr/missions/palestine-bande-de-gaza/', 2),
('islamic-relief', 'Islamic Relief', 'Appel d’urgence Palestine — aide humanitaire sur le terrain.', 'Islamic Relief est une ONG humanitaire internationale qui intervient dans de nombreux pays. En Palestine, l’organisation mène des actions d’urgence : nourriture, abris, santé et soutien aux familles déracinées.\n\nLes équipes travaillent avec des partenaires locaux pour acheminer l’aide au plus près des besoins, y compris lors de distributions pendant le Ramadan et les périodes critiques.\n\nVotre don contribue à des distributions alimentaires et à une assistance directe sur le terrain.', 'https://islamic-relief.org/wp-content/uploads/2025/11/palestine-banner-food-distribution-in-Ramadan.png', 'https://islamic-relief.org/wp-content/uploads/2025/02/cropped-1200x1200px-IR-logo-1.jpg', '[]', 'https://islamic-relief.org/appeals/palestine-emergency-appeal/', 3),
('unrwa', 'UNRWA', 'Agence de l’ONU pour les réfugiés palestiniens — école, santé, aide sociale pour des millions de personnes.', 'L’UNRWA (United Nations Relief and Works Agency for Palestine Refugees in the Near East) est l’agence de l’ONU dédiée aux réfugiés palestiniens. Elle assure l’éducation dans ses écoles, des soins de santé primaires, une aide sociale et des services d’urgence pour des millions de personnes en Palestine, au Liban, en Jordanie et en Syrie.\n\nFace aux crises prolongées, l’UNRWA reste un pilier pour des centaines de milliers d’enfants scolarisés et pour l’accès aux soins.\n\nSoutenir l’UNRWA, c’est aider à maintenir ces services essentiels pour une population déjà gravement éprouvée.', 'https://donate.unrwa.org/sites/default/files/styles/social_large/public/2025-05/website_banners_1250_x_1500_px_4.png?h=b15027c8&itok=GzmWZAf3', 'static/donations/unrwa.svg', '[]', 'https://donate.unrwa.org/', 4);

CREATE TABLE IF NOT EXISTS donation_suggestions (
    id INT NOT NULL AUTO_INCREMENT,
    nom VARCHAR(500) NOT NULL,
    description TEXT NULL,
    lien_source VARCHAR(2000) NULL,
    email_contact VARCHAR(320) NULL,
    created_at VARCHAR(64) NOT NULL,
    statut VARCHAR(32) NOT NULL DEFAULT 'en_attente',
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
