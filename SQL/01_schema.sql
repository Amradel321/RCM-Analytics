CREATE DATABASE rcm_analytics;
USE rcm_analytics;

CREATE TABLE dim_payer (
  payer_key INT PRIMARY KEY AUTO_INCREMENT,
  payer_name VARCHAR(100),
  payer_type VARCHAR(30),          -- Commercial, Medicare, Medicaid, Self-pay
  timely_filing_days INT
);

CREATE TABLE dim_provider (
  provider_key INT PRIMARY KEY AUTO_INCREMENT,
  provider_name VARCHAR(100),
  specialty VARCHAR(50)
);

CREATE TABLE dim_procedure (
  procedure_key INT PRIMARY KEY AUTO_INCREMENT,
  cpt_code VARCHAR(10),
  description VARCHAR(150),
  base_charge DECIMAL(10,2),
  requires_prior_auth BOOLEAN
);

CREATE TABLE dim_denial_code (
  carc_code VARCHAR(10) PRIMARY KEY,
  description VARCHAR(200),
  denial_category VARCHAR(40)      -- Eligibility, Authorization, Coding, Timely Filing, Medical Necessity
);

CREATE TABLE dim_date (
  date_key INT PRIMARY KEY,        -- YYYYMMDD
  full_date DATE,
  year SMALLINT,
  quarter TINYINT,
  month TINYINT,
  month_name VARCHAR(12)
);

CREATE TABLE fact_claim_line (
  claim_line_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  claim_id VARCHAR(20),
  patient_id VARCHAR(20),
  payer_key INT,
  provider_key INT,
  procedure_key INT,
  dos_date_key INT,                -- date of service
  submit_date_key INT,
  payment_date_key INT NULL,
  billed_amount DECIMAL(10,2),
  allowed_amount DECIMAL(10,2),
  paid_amount DECIMAL(10,2),
  patient_resp DECIMAL(10,2),
  claim_status VARCHAR(20),        -- Paid, Denied, Appealed, Written-off
  carc_code VARCHAR(10) NULL,
  is_first_pass_paid BOOLEAN,
  FOREIGN KEY (payer_key) REFERENCES dim_payer(payer_key),
  FOREIGN KEY (provider_key) REFERENCES dim_provider(provider_key),
  FOREIGN KEY (procedure_key) REFERENCES dim_procedure(procedure_key),
  FOREIGN KEY (carc_code) REFERENCES dim_denial_code(carc_code)
);