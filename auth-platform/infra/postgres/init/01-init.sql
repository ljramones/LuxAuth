-- =====================================================================
-- Auth Platform Database Initialization
-- =====================================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- =====================================================================
-- Tables
-- =====================================================================

CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE devices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    device_serial VARCHAR(255) NOT NULL,
    device_type VARCHAR(100) NOT NULL,
    firmware_version VARCHAR(50),
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE device_calibrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID NOT NULL REFERENCES devices(id),
    calibration_profile JSONB NOT NULL,
    calibrated_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE scan_recipes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recipe_key VARCHAR(255) NOT NULL,
    brand VARCHAR(255) NOT NULL,
    category VARCHAR(255) NOT NULL,
    material VARCHAR(255) NOT NULL,
    version INT NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE scan_recipe_regions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scan_recipe_id UUID NOT NULL REFERENCES scan_recipes(id),
    region_code VARCHAR(100) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    min_images INT NOT NULL DEFAULT 1,
    magnification_profile VARCHAR(100),
    lighting_profile VARCHAR(100),
    sort_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE scan_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id),
    operator_id UUID REFERENCES users(id),
    device_id UUID REFERENCES devices(id),
    scan_recipe_id UUID REFERENCES scan_recipes(id),
    claimed_brand VARCHAR(255),
    claimed_category VARCHAR(255),
    claimed_material VARCHAR(255),
    claimed_model VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'CAPTURING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE image_assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scan_session_id UUID,
    source_type VARCHAR(100) NOT NULL DEFAULT 'SCAN_SESSION',
    source_id UUID,
    tenant_id UUID,
    region_code VARCHAR(100) NOT NULL,
    device_id UUID,
    raw_object_uri VARCHAR(1024) NOT NULL,
    capture_settings JSONB,
    checksum VARCHAR(128),
    file_size_bytes BIGINT,
    content_type VARCHAR(100),
    width INT,
    height INT,
    image_format VARCHAR(20),
    color_mode VARCHAR(20),
    sha256_checksum VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE image_quality_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    image_asset_id UUID NOT NULL UNIQUE REFERENCES image_assets(id),
    sharpness_score FLOAT,
    exposure_score FLOAT,
    glare_score FLOAT,
    quality_status VARCHAR(50),
    issues JSONB DEFAULT '[]',
    model_version VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE normalized_images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    image_asset_id UUID NOT NULL UNIQUE REFERENCES image_assets(id),
    normalized_object_uri VARCHAR(1024) NOT NULL,
    preprocessing_version VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    image_asset_id UUID NOT NULL UNIQUE,
    embedding vector NOT NULL,
    embedding_model_version VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE reference_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    authenticity_status VARCHAR(50) NOT NULL,
    brand VARCHAR(255) NOT NULL,
    category VARCHAR(255) NOT NULL,
    model VARCHAR(255),
    material VARCHAR(255),
    production_year INT,
    source VARCHAR(255),
    chain_of_custody TEXT,
    label_confidence VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE reference_images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reference_item_id UUID NOT NULL REFERENCES reference_items(id),
    region_code VARCHAR(100) NOT NULL,
    device_profile VARCHAR(100),
    lighting_profile VARCHAR(100),
    object_uri VARCHAR(1024) NOT NULL,
    quality_status VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE region_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    image_asset_id UUID NOT NULL,
    scan_session_id UUID NOT NULL,
    region_code VARCHAR(100) NOT NULL,
    authentic_similarity FLOAT,
    counterfeit_similarity FLOAT,
    ood_score FLOAT,
    region_decision VARCHAR(50),
    nearest_authentic_ids JSONB,
    nearest_counterfeit_ids JSONB,
    model_version VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE authentication_decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scan_session_id UUID NOT NULL UNIQUE,
    result VARCHAR(50) NOT NULL,
    summary JSONB,
    region_results JSONB,
    decision_rule_version VARCHAR(100),
    embedding_model_version VARCHAR(100),
    reference_dataset_version VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE review_cases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scan_session_id UUID NOT NULL REFERENCES scan_sessions(id),
    authentication_decision_id UUID NOT NULL REFERENCES authentication_decisions(id),
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    reviewer_id UUID,
    reviewer_notes TEXT,
    reviewer_decision VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE certificates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scan_session_id UUID NOT NULL REFERENCES scan_sessions(id),
    authentication_decision_id UUID NOT NULL REFERENCES authentication_decisions(id),
    certificate_number VARCHAR(100) UNIQUE NOT NULL,
    brand VARCHAR(255),
    category VARCHAR(255),
    material VARCHAR(255),
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE audit_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(100) NOT NULL,
    correlation_id UUID,
    tenant_id UUID,
    scan_session_id UUID,
    image_id UUID,
    actor_id UUID,
    payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE model_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name VARCHAR(255) NOT NULL,
    model_version VARCHAR(100) NOT NULL,
    model_type VARCHAR(100) NOT NULL,
    artifact_uri VARCHAR(1024),
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE processing_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    idempotency_key VARCHAR(512) NOT NULL UNIQUE,
    stage VARCHAR(100) NOT NULL,
    scan_session_id UUID,
    image_id UUID,
    status VARCHAR(50) NOT NULL DEFAULT 'STARTED',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE training_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name VARCHAR(255) NOT NULL,
    model_version VARCHAR(100) NOT NULL,
    dataset_version VARCHAR(255) NOT NULL,
    embedding_dimension INT,
    loss_type VARCHAR(100),
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    config_json JSONB,
    metrics_json JSONB,
    artifact_uri VARCHAR(1024),
    metadata_uri VARCHAR(1024),
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE ml_experiments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    experiment_name VARCHAR(255) NOT NULL,
    description TEXT,
    dataset_version VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE ml_experiment_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    experiment_id UUID REFERENCES ml_experiments(id),
    training_run_id UUID REFERENCES training_runs(id),
    model_name VARCHAR(255),
    model_version VARCHAR(100),
    dataset_version VARCHAR(255),
    config_json JSONB,
    metrics_json JSONB,
    artifact_uri VARCHAR(1024),
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================================
-- Capture Intake
-- =====================================================================

CREATE TABLE capture_protocols (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    protocol_code VARCHAR(255) NOT NULL UNIQUE,
    protocol_version VARCHAR(50) NOT NULL DEFAULT 'v0.1.0',
    brand VARCHAR(255),
    category VARCHAR(255),
    material VARCHAR(255),
    description TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE capture_protocol_regions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    capture_protocol_id UUID NOT NULL REFERENCES capture_protocols(id),
    region_code VARCHAR(100) NOT NULL,
    display_name VARCHAR(255),
    min_images INT NOT NULL DEFAULT 1,
    magnification_profile VARCHAR(100),
    lighting_profile VARCHAR(100),
    sort_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE capture_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    device_id UUID REFERENCES devices(id),
    calibration_id UUID REFERENCES device_calibrations(id),
    capture_protocol_id UUID REFERENCES capture_protocols(id),
    source_type VARCHAR(100) NOT NULL DEFAULT 'api',
    operator VARCHAR(255),
    status VARCHAR(50) NOT NULL DEFAULT 'CREATED',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE capture_session_images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    capture_session_id UUID NOT NULL REFERENCES capture_sessions(id),
    image_asset_id UUID REFERENCES image_assets(id),
    external_item_id VARCHAR(255),
    region_code VARCHAR(100) NOT NULL,
    capture_index INT NOT NULL DEFAULT 0,
    device_id UUID REFERENCES devices(id),
    raw_object_uri VARCHAR(1024) NOT NULL,
    file_size_bytes BIGINT,
    content_type VARCHAR(100),
    width INT,
    height INT,
    image_format VARCHAR(20),
    sha256_checksum VARCHAR(64),
    magnification_profile VARCHAR(100),
    lighting_profile VARCHAR(100),
    calibration_profile VARCHAR(255),
    authenticity_status VARCHAR(50),
    label_confidence VARCHAR(50),
    provenance_type VARCHAR(100),
    notes TEXT,
    quality_status VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================================
-- Capture Batch (manifest/folder-driven lab ingestion)
-- =====================================================================

CREATE TABLE capture_batches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    batch_code VARCHAR(255) NOT NULL UNIQUE,
    dataset_candidate_name VARCHAR(255),
    capture_protocol_id UUID REFERENCES capture_protocols(id),
    device_id UUID REFERENCES devices(id),
    calibration_profile_id UUID REFERENCES device_calibrations(id),
    source_type VARCHAR(100) NOT NULL DEFAULT 'lab_capture',
    status VARCHAR(50) NOT NULL DEFAULT 'CREATED',
    created_by VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE capture_batch_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    capture_batch_id UUID NOT NULL REFERENCES capture_batches(id),
    external_item_id VARCHAR(255) NOT NULL,
    brand VARCHAR(255),
    category VARCHAR(255),
    material VARCHAR(255),
    model VARCHAR(255),
    production_year INT,
    authenticity_status VARCHAR(50) NOT NULL,
    label_confidence VARCHAR(50) NOT NULL DEFAULT 'high',
    provenance_type VARCHAR(100) NOT NULL DEFAULT 'synthetic',
    status VARCHAR(50) NOT NULL DEFAULT 'CREATED',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE capture_batch_images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    capture_batch_id UUID NOT NULL REFERENCES capture_batches(id),
    capture_batch_item_id UUID NOT NULL REFERENCES capture_batch_items(id),
    external_image_id VARCHAR(255),
    region_code VARCHAR(100) NOT NULL,
    source_file_path TEXT,
    raw_object_uri TEXT,
    normalized_object_uri TEXT,
    sha256_checksum VARCHAR(64),
    perceptual_hash VARCHAR(64),
    width INT,
    height INT,
    image_format VARCHAR(20),
    color_mode VARCHAR(20),
    quality_status VARCHAR(50),
    issues JSONB,
    status VARCHAR(50) NOT NULL DEFAULT 'CREATED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE capture_batch_validation_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    capture_batch_id UUID NOT NULL REFERENCES capture_batches(id),
    status VARCHAR(50) NOT NULL,
    summary_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================================
-- Item Condition and Component Provenance
-- =====================================================================

CREATE TABLE item_condition_metadata (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reference_item_id UUID REFERENCES reference_items(id),
    capture_batch_item_id UUID REFERENCES capture_batch_items(id),
    capture_session_id UUID REFERENCES capture_sessions(id),
    condition_grade VARCHAR(100),
    known_authenticity_basis TEXT,
    known_repairs BOOLEAN NOT NULL DEFAULT FALSE,
    third_party_repair BOOLEAN NOT NULL DEFAULT FALSE,
    restoration_notes TEXT,
    provenance_notes TEXT,
    condition_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE item_component_conditions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    item_condition_metadata_id UUID NOT NULL REFERENCES item_condition_metadata(id),
    region_code VARCHAR(100) NOT NULL,
    component_type VARCHAR(100),
    component_status VARCHAR(100),
    source VARCHAR(255),
    confidence VARCHAR(50),
    exclude_from_auth_decision BOOLEAN NOT NULL DEFAULT FALSE,
    expected_to_mismatch BOOLEAN NOT NULL DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================================
-- Dataset Governance
-- =====================================================================

CREATE TABLE reference_dataset_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dataset_version VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    source_type VARCHAR(100) NOT NULL DEFAULT 'synthetic',
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    created_by VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE reference_dataset_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    dataset_version_id UUID NOT NULL REFERENCES reference_dataset_versions(id),
    reference_image_id UUID NOT NULL REFERENCES reference_images(id),
    split VARCHAR(50) NOT NULL DEFAULT 'train',
    include_in_search BOOLEAN NOT NULL DEFAULT TRUE,
    include_in_evaluation BOOLEAN NOT NULL DEFAULT FALSE,
    include_in_training BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE reference_label_reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reference_item_id UUID NOT NULL REFERENCES reference_items(id),
    reference_image_id UUID REFERENCES reference_images(id),
    reviewer_id VARCHAR(255),
    authenticity_status VARCHAR(50) NOT NULL,
    label_confidence VARCHAR(50) NOT NULL DEFAULT 'high',
    provenance_type VARCHAR(100) NOT NULL DEFAULT 'synthetic',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE threshold_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    profile_name VARCHAR(255) NOT NULL UNIQUE,
    profile_version VARCHAR(50) NOT NULL,
    embedding_model_version VARCHAR(100) NOT NULL,
    reference_dataset_version VARCHAR(255) NOT NULL,
    strong_match_threshold FLOAT NOT NULL DEFAULT 0.85,
    mismatch_threshold FLOAT NOT NULL DEFAULT 0.50,
    ood_threshold FLOAT NOT NULL DEFAULT 0.40,
    counterfeit_similarity_threshold FLOAT NOT NULL DEFAULT 0.50,
    min_required_regions INT NOT NULL DEFAULT 5,
    require_all_regions BOOLEAN NOT NULL DEFAULT TRUE,
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================================
-- Evaluation
-- =====================================================================

CREATE TABLE evaluation_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    evaluation_name VARCHAR(255) NOT NULL,
    reference_dataset_version VARCHAR(255) NOT NULL,
    embedding_model_version VARCHAR(100) NOT NULL,
    preprocessing_version VARCHAR(100),
    threshold_profile VARCHAR(255) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status VARCHAR(50) NOT NULL DEFAULT 'RUNNING',
    summary_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE evaluation_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    evaluation_run_id UUID NOT NULL REFERENCES evaluation_runs(id),
    scan_session_id UUID,
    image_asset_id UUID,
    reference_image_id UUID,
    expected_label VARCHAR(50) NOT NULL,
    predicted_label VARCHAR(50),
    result VARCHAR(50),
    region_code VARCHAR(100),
    authentic_similarity FLOAT,
    counterfeit_similarity FLOAT,
    ood_score FLOAT,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =====================================================================
-- Indexes
-- =====================================================================

CREATE INDEX idx_users_organization_id ON users(organization_id);
CREATE INDEX idx_users_email ON users(email);

CREATE INDEX idx_devices_organization_id ON devices(organization_id);
CREATE INDEX idx_devices_device_serial ON devices(device_serial);

CREATE INDEX idx_device_calibrations_device_id ON device_calibrations(device_id);

CREATE INDEX idx_scan_recipes_recipe_key ON scan_recipes(recipe_key);
CREATE INDEX idx_scan_recipes_brand_category ON scan_recipes(brand, category);

CREATE INDEX idx_scan_recipe_regions_recipe_id ON scan_recipe_regions(scan_recipe_id);

CREATE INDEX idx_scan_sessions_organization_id ON scan_sessions(organization_id);
CREATE INDEX idx_scan_sessions_operator_id ON scan_sessions(operator_id);
CREATE INDEX idx_scan_sessions_device_id ON scan_sessions(device_id);
CREATE INDEX idx_scan_sessions_status ON scan_sessions(status);

CREATE INDEX idx_image_assets_scan_session_id ON image_assets(scan_session_id);
CREATE INDEX idx_image_assets_source ON image_assets(source_type, source_id);
CREATE INDEX idx_image_assets_tenant_id ON image_assets(tenant_id);
CREATE INDEX idx_image_assets_device_id ON image_assets(device_id);
CREATE INDEX idx_image_assets_region_code ON image_assets(region_code);

CREATE INDEX idx_image_quality_reports_image_asset_id ON image_quality_reports(image_asset_id);

CREATE INDEX idx_normalized_images_image_asset_id ON normalized_images(image_asset_id);

CREATE INDEX idx_embeddings_image_asset_id ON embeddings(image_asset_id);

CREATE INDEX idx_reference_items_brand_category ON reference_items(brand, category);
CREATE INDEX idx_reference_items_authenticity ON reference_items(authenticity_status);

CREATE INDEX idx_reference_images_reference_item_id ON reference_images(reference_item_id);
CREATE INDEX idx_reference_images_region_code ON reference_images(region_code);

CREATE INDEX idx_region_scores_image_asset_id ON region_scores(image_asset_id);
CREATE INDEX idx_region_scores_scan_session_id ON region_scores(scan_session_id);

CREATE INDEX idx_review_cases_scan_session_id ON review_cases(scan_session_id);
CREATE INDEX idx_review_cases_status ON review_cases(status);

CREATE INDEX idx_certificates_scan_session_id ON certificates(scan_session_id);
CREATE INDEX idx_certificates_certificate_number ON certificates(certificate_number);

CREATE INDEX idx_audit_events_event_type ON audit_events(event_type);
CREATE INDEX idx_audit_events_correlation_id ON audit_events(correlation_id);
CREATE INDEX idx_audit_events_scan_session_id ON audit_events(scan_session_id);
CREATE INDEX idx_audit_events_created_at ON audit_events(created_at);

CREATE INDEX idx_model_versions_model_name ON model_versions(model_name);
CREATE INDEX idx_model_versions_is_active ON model_versions(is_active);

CREATE INDEX idx_processing_runs_idempotency_key ON processing_runs(idempotency_key);
CREATE INDEX idx_processing_runs_stage ON processing_runs(stage);
CREATE INDEX idx_processing_runs_status ON processing_runs(status);
CREATE INDEX idx_processing_runs_scan_session_id ON processing_runs(scan_session_id);

CREATE INDEX idx_training_runs_status ON training_runs(status);
CREATE INDEX idx_training_runs_model ON training_runs(model_name, model_version);

CREATE INDEX idx_ref_dataset_versions_status ON reference_dataset_versions(status);
CREATE INDEX idx_ref_dataset_members_version ON reference_dataset_members(dataset_version_id);
CREATE INDEX idx_ref_dataset_members_image ON reference_dataset_members(reference_image_id);
CREATE INDEX idx_ref_dataset_members_split ON reference_dataset_members(split);
CREATE INDEX idx_ref_label_reviews_item ON reference_label_reviews(reference_item_id);
CREATE INDEX idx_ref_label_reviews_image ON reference_label_reviews(reference_image_id);
CREATE INDEX idx_threshold_profiles_status ON threshold_profiles(status);
CREATE INDEX idx_evaluation_runs_status ON evaluation_runs(status);
CREATE INDEX idx_evaluation_items_run ON evaluation_items(evaluation_run_id);
CREATE INDEX idx_evaluation_items_result ON evaluation_items(result);
CREATE INDEX idx_ml_experiments_name ON ml_experiments(experiment_name);
CREATE INDEX idx_ml_experiment_runs_experiment ON ml_experiment_runs(experiment_id);
CREATE INDEX idx_ml_experiment_runs_model ON ml_experiment_runs(model_name, model_version);

CREATE INDEX idx_capture_protocols_code ON capture_protocols(protocol_code);
CREATE INDEX idx_capture_protocol_regions_protocol ON capture_protocol_regions(capture_protocol_id);
CREATE INDEX idx_capture_sessions_device ON capture_sessions(device_id);
CREATE INDEX idx_capture_sessions_status ON capture_sessions(status);
CREATE INDEX idx_capture_session_images_session ON capture_session_images(capture_session_id);
CREATE INDEX idx_capture_session_images_asset ON capture_session_images(image_asset_id);
CREATE INDEX idx_capture_session_images_region ON capture_session_images(region_code);
CREATE INDEX idx_capture_session_images_item ON capture_session_images(external_item_id);

CREATE INDEX idx_capture_batches_code ON capture_batches(batch_code);
CREATE INDEX idx_capture_batches_status ON capture_batches(status);
CREATE INDEX idx_capture_batch_items_batch ON capture_batch_items(capture_batch_id);
CREATE INDEX idx_capture_batch_items_ext_id ON capture_batch_items(external_item_id);
CREATE INDEX idx_capture_batch_images_batch ON capture_batch_images(capture_batch_id);
CREATE INDEX idx_capture_batch_images_item ON capture_batch_images(capture_batch_item_id);
CREATE INDEX idx_capture_batch_images_sha ON capture_batch_images(sha256_checksum);
CREATE INDEX idx_capture_batch_validation_batch ON capture_batch_validation_reports(capture_batch_id);

CREATE INDEX idx_item_condition_ref_item ON item_condition_metadata(reference_item_id);
CREATE INDEX idx_item_condition_batch_item ON item_condition_metadata(capture_batch_item_id);
CREATE INDEX idx_item_component_cond_meta ON item_component_conditions(item_condition_metadata_id);
CREATE INDEX idx_item_component_cond_region ON item_component_conditions(region_code);

-- =====================================================================
-- Seed Data
-- =====================================================================

-- Organization
INSERT INTO organizations (id, name) VALUES
    ('a0000000-0000-0000-0000-000000000001', 'LuxVerify Demo Corp');

-- User (operator)
INSERT INTO users (id, organization_id, email, name, role) VALUES
    ('b0000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001',
     'operator@luxverify.demo', 'Demo Operator', 'OPERATOR');

-- Device
INSERT INTO devices (id, organization_id, device_serial, device_type, firmware_version, status) VALUES
    ('c0000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001',
     'LVD-2024-00001', 'HANDHELD_MICROSCOPE', '2.4.1', 'ACTIVE');

-- Scan Recipe: Louis Vuitton Monogram Canvas Handbag
INSERT INTO scan_recipes (id, recipe_key, brand, category, material, version, is_active) VALUES
    ('d0000000-0000-0000-0000-000000000001', 'lv_monogram_canvas_handbag_v1',
     'Louis Vuitton', 'handbag', 'monogram_canvas', 1, TRUE);

INSERT INTO scan_recipe_regions (id, scan_recipe_id, region_code, display_name, min_images, magnification_profile, lighting_profile, sort_order) VALUES
    ('e0000000-0000-0000-0000-000000000001', 'd0000000-0000-0000-0000-000000000001',
     'EXTERIOR_CANVAS', 'Exterior Canvas Pattern', 1, '10x', 'DIFFUSE', 1),
    ('e0000000-0000-0000-0000-000000000002', 'd0000000-0000-0000-0000-000000000001',
     'FRONT_LOGO_PRINT', 'Front Logo Print', 1, '20x', 'DIFFUSE', 2),
    ('e0000000-0000-0000-0000-000000000003', 'd0000000-0000-0000-0000-000000000001',
     'INTERIOR_HEAT_STAMP', 'Interior Heat Stamp', 1, '20x', 'RAKING', 3),
    ('e0000000-0000-0000-0000-000000000004', 'd0000000-0000-0000-0000-000000000001',
     'HARDWARE_ENGRAVING', 'Hardware Engraving', 1, '30x', 'ANGLED', 4),
    ('e0000000-0000-0000-0000-000000000005', 'd0000000-0000-0000-0000-000000000001',
     'STITCHING_DETAIL', 'Stitching Detail', 1, '20x', 'DIRECTIONAL', 5);

-- Reference Items
INSERT INTO reference_items (id, authenticity_status, brand, category, model, material, production_year, source, chain_of_custody, label_confidence) VALUES
    ('f0000000-0000-0000-0000-000000000001', 'CONFIRMED_AUTHENTIC',
     'Louis Vuitton', 'handbag', 'Speedy 30', 'monogram_canvas', 2022,
     'Brand Partner', 'Provided directly by LVMH authentication team', 'HIGH'),
    ('f0000000-0000-0000-0000-000000000002', 'CONFIRMED_AUTHENTIC',
     'Louis Vuitton', 'handbag', 'Neverfull MM', 'monogram_canvas', 2023,
     'Brand Partner', 'Provided directly by LVMH authentication team', 'HIGH'),
    ('f0000000-0000-0000-0000-000000000003', 'CONFIRMED_COUNTERFEIT',
     'Louis Vuitton', 'handbag', 'Speedy 30', 'monogram_canvas', 2023,
     'Customs Seizure', 'Seized by US CBP, case ref CBP-2023-44891', 'HIGH');

-- Reference Images
INSERT INTO reference_images (id, reference_item_id, region_code, device_profile, lighting_profile, object_uri, quality_status) VALUES
    ('10000000-0000-0000-0000-000000000001', 'f0000000-0000-0000-0000-000000000001',
     'EXTERIOR_CANVAS', 'HANDHELD_MICROSCOPE_v2', 'DIFFUSE',
     's3://auth-platform-reference-library/lv/authentic/speedy30/exterior_canvas_001.png', 'PASS'),
    ('10000000-0000-0000-0000-000000000002', 'f0000000-0000-0000-0000-000000000001',
     'STITCHING_EDGE', 'HANDHELD_MICROSCOPE_v2', 'DIRECTIONAL',
     's3://auth-platform-reference-library/lv/authentic/speedy30/stitching_edge_001.png', 'PASS'),
    ('10000000-0000-0000-0000-000000000003', 'f0000000-0000-0000-0000-000000000002',
     'EXTERIOR_CANVAS', 'HANDHELD_MICROSCOPE_v2', 'DIFFUSE',
     's3://auth-platform-reference-library/lv/authentic/neverfull/exterior_canvas_001.png', 'PASS'),
    ('10000000-0000-0000-0000-000000000004', 'f0000000-0000-0000-0000-000000000003',
     'EXTERIOR_CANVAS', 'HANDHELD_MICROSCOPE_v2', 'DIFFUSE',
     's3://auth-platform-reference-library/lv/counterfeit/speedy30/exterior_canvas_001.png', 'PASS'),
    ('10000000-0000-0000-0000-000000000005', 'f0000000-0000-0000-0000-000000000003',
     'STITCHING_EDGE', 'HANDHELD_MICROSCOPE_v2', 'DIRECTIONAL',
     's3://auth-platform-reference-library/lv/counterfeit/speedy30/stitching_edge_001.png', 'PASS');

-- Default capture protocol
INSERT INTO capture_protocols (id, protocol_code, protocol_version, brand, category, material, description) VALUES
    ('40000000-0000-0000-0000-000000000001', 'lv_monogram_canvas_handbag_capture', 'v0.1.0',
     'Louis Vuitton', 'handbag', 'monogram_canvas', 'Default capture protocol for LV monogram canvas handbags');

INSERT INTO capture_protocol_regions (id, capture_protocol_id, region_code, display_name, min_images, magnification_profile, lighting_profile, sort_order) VALUES
    ('41000000-0000-0000-0000-000000000001', '40000000-0000-0000-0000-000000000001',
     'EXTERIOR_CANVAS', 'Exterior Canvas Pattern', 3, '10x', 'DIFFUSE', 1),
    ('41000000-0000-0000-0000-000000000002', '40000000-0000-0000-0000-000000000001',
     'FRONT_LOGO_PRINT', 'Front Logo Print', 2, '20x', 'DIFFUSE', 2),
    ('41000000-0000-0000-0000-000000000003', '40000000-0000-0000-0000-000000000001',
     'INTERIOR_HEAT_STAMP', 'Interior Heat Stamp', 2, '20x', 'RAKING', 3),
    ('41000000-0000-0000-0000-000000000004', '40000000-0000-0000-0000-000000000001',
     'HARDWARE_ENGRAVING', 'Hardware Engraving', 2, '30x', 'ANGLED', 4),
    ('41000000-0000-0000-0000-000000000005', '40000000-0000-0000-0000-000000000001',
     'STITCHING_DETAIL', 'Stitching Detail', 3, '20x', 'DIRECTIONAL', 5);

-- Reference Embeddings table
CREATE TABLE reference_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reference_image_id UUID NOT NULL REFERENCES reference_images(id),
    embedding vector NOT NULL,
    embedding_model_version VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_reference_embeddings_ref_image ON reference_embeddings(reference_image_id);
-- Note: HNSW index requires fixed-dimension vectors. Omitted because the column
-- now accepts variable dimensions (128 for v0.1.0, 256 for v0.2.0). Add
-- dimension-specific indexes when query patterns are known.

-- Default threshold profile
INSERT INTO threshold_profiles (id, profile_name, profile_version, embedding_model_version, reference_dataset_version, strong_match_threshold, mismatch_threshold, ood_threshold, counterfeit_similarity_threshold, min_required_regions, require_all_regions, status) VALUES
    ('30000000-0000-0000-0000-000000000001', 'texture_baseline_default', 'v0.1.0', 'texture_baseline_v0.1.0', 'synthetic_lv_monogram_v0.1.0', 0.85, 0.50, 0.40, 0.50, 5, TRUE, 'active'),
    ('30000000-0000-0000-0000-000000000002', 'learned_metric_default', 'v0.1.0', 'learned_metric_v0.1.0', 'synthetic_lv_monogram_v0.1.0', 0.80, 0.55, 0.45, 0.55, 5, TRUE, 'active');

-- Model Version
INSERT INTO model_versions (id, model_name, model_version, model_type, artifact_uri, description, is_active) VALUES
    ('20000000-0000-0000-0000-000000000001', 'luxury-embed-v1', '1.0.0-stub', 'EMBEDDING',
     's3://auth-platform-ml-artifacts/models/luxury-embed-v1/1.0.0-stub/',
     'Stub embedding model for local development. Produces deterministic 128-dim vectors.', TRUE),
    ('20000000-0000-0000-0000-000000000002', 'dinov2_base_frozen', 'dinov2_base_frozen_v0.1.0', 'EMBEDDING',
     'hf://facebook/dinov2-base@f9e44c814b77203eaa57a6bdbbd535f21ede1415',
     'DINOv2 ViT-B/14 frozen, CLS token, L2-normalized 768-d. Foundation-model encoder used as a comparison backbone in Phase 10 few-shot experiments. Diagnostic only on public texture data.', TRUE);

-- Seed 128-dim embeddings for reference images into reference_embeddings
DO $$
DECLARE
    img_ids UUID[] := ARRAY[
        '10000000-0000-0000-0000-000000000001',
        '10000000-0000-0000-0000-000000000002',
        '10000000-0000-0000-0000-000000000003',
        '10000000-0000-0000-0000-000000000004',
        '10000000-0000-0000-0000-000000000005'
    ];
    img_id UUID;
    seed_val INT;
    vec_text TEXT;
    i INT;
BEGIN
    FOR idx IN 1..array_length(img_ids, 1) LOOP
        img_id := img_ids[idx];
        seed_val := idx;
        vec_text := '[';
        FOR i IN 1..128 LOOP
            vec_text := vec_text || round(sin(seed_val * i * 0.1)::numeric, 6)::text;
            IF i < 128 THEN
                vec_text := vec_text || ',';
            END IF;
        END LOOP;
        vec_text := vec_text || ']';
        EXECUTE format(
            'INSERT INTO reference_embeddings (id, reference_image_id, embedding, embedding_model_version, created_at) VALUES (uuid_generate_v4(), %L, %L::vector, %L, NOW())',
            img_id, vec_text, 'texture_baseline_v0.1.0'
        );
    END LOOP;
END $$;

-- Note: HNSW index omitted — embeddings column accepts variable dimensions.
