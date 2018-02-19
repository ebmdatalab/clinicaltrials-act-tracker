WITH full_data_extract AS (
SELECT
  TRIM(json_EXTRACT(json,
      "$.clinical_study.id_info.nct_id"), '"') AS nct_id,
  TRIM(json_EXTRACT(json,
      "$.clinical_study.study_type"), '"') AS study_type,
  TRIM(json_EXTRACT(json,
      "$.clinical_study.overall_status"), '"') AS study_status,
  TRIM(TRIM(json_EXTRACT(json,
        "$.clinical_study.phase"), '"')) AS phase,
   json_EXTRACT(json,
    "$.clinical_study.intervention") AS intervention_type,
  CASE
    WHEN json_EXTRACT(json,  "$.clinical_study.start_date.text") IS NOT NULL THEN (IF(REGEXP_CONTAINS(JSON_EXTRACT_SCALAR(json,  "$.clinical_study.start_date.text"), r"\d,"),  PARSE_DATE("%B %e, %Y",  JSON_EXTRACT_SCALAR(json,  "$.clinical_study.start_date.text")),  DATE_SUB(DATE_ADD(PARSE_DATE("%B %Y",  JSON_EXTRACT_SCALAR(json,  "$.clinical_study.start_date.text")), INTERVAL 1 MONTH), INTERVAL 1 DAY)))
    ELSE (IF(REGEXP_CONTAINS(JSON_EXTRACT_SCALAR(json,
          "$.clinical_study.start_date"), r"\d,"),
      PARSE_DATE("%B %e, %Y",
        JSON_EXTRACT_SCALAR(json,
          "$.clinical_study.start_date")),
      DATE_SUB(DATE_ADD(PARSE_DATE("%B %Y",
            JSON_EXTRACT_SCALAR(json,
              "$.clinical_study.start_date")), INTERVAL 1 MONTH), INTERVAL 1 DAY)))
  END AS start_date,
  CASE
    WHEN json_EXTRACT(json,  "$.clinical_study.primary_completion_date.text") IS NULL THEN
    (CASE
    WHEN json_EXTRACT(json,  "$.clinical_study.completion_date.text") IS NOT NULL THEN (IF(REGEXP_CONTAINS(JSON_EXTRACT_SCALAR(json,  "$.clinical_study.completion_date.text"), r"\d,"),  PARSE_DATE("%B %e, %Y",  JSON_EXTRACT_SCALAR(json,  "$.clinical_study.completion_date.text")),  DATE_SUB(DATE_ADD(PARSE_DATE("%B %Y",  JSON_EXTRACT_SCALAR(json,  "$.clinical_study.completion_date.text")), INTERVAL 1 MONTH), INTERVAL 1 DAY)))
    ELSE (IF(REGEXP_CONTAINS(JSON_EXTRACT_SCALAR(json,
          "$.clinical_study.completion_date"), r"\d,"),
      PARSE_DATE("%B %e, %Y",
        JSON_EXTRACT_SCALAR(json,
          "$.clinical_study.completion_date")),
      DATE_SUB(DATE_ADD(PARSE_DATE("%B %Y",
            JSON_EXTRACT_SCALAR(json,
              "$.clinical_study.completion_date")), INTERVAL 1 MONTH), INTERVAL 1 DAY))) END)
    ELSE ( IF(REGEXP_CONTAINS(JSON_EXTRACT_SCALAR(json,
          "$.clinical_study.primary_completion_date.text"), r"\d,"),
      PARSE_DATE("%B %e, %Y",
        JSON_EXTRACT_SCALAR(json,
          "$.clinical_study.primary_completion_date.text")),
      DATE_SUB(DATE_ADD(PARSE_DATE("%B %Y",
            JSON_EXTRACT_SCALAR(json,
              "$.clinical_study.primary_completion_date.text")), INTERVAL 1 MONTH), INTERVAL 1 DAY)))
  END AS available_completion_date,
  IF(REGEXP_CONTAINS(JSON_EXTRACT_SCALAR(json,
        "$.clinical_study.primary_completion_date.text"), r"\d,"),
    PARSE_DATE("%B %e, %Y",
      JSON_EXTRACT_SCALAR(json,
        "$.clinical_study.primary_completion_date.text")),
    DATE_SUB(DATE_ADD(PARSE_DATE("%B %Y",
          JSON_EXTRACT_SCALAR(json,
            "$.clinical_study.primary_completion_date.text")), INTERVAL 1 MONTH), INTERVAL 1 DAY)) AS primary_completion_date,
  CASE
    WHEN json_EXTRACT(json,  "$.clinical_study.completion_date.text") IS NOT NULL THEN (IF(REGEXP_CONTAINS(JSON_EXTRACT_SCALAR(json,  "$.clinical_study.completion_date.text"), r"\d,"),  PARSE_DATE("%B %e, %Y",  JSON_EXTRACT_SCALAR(json,  "$.clinical_study.completion_date.text")),  DATE_SUB(DATE_ADD(PARSE_DATE("%B %Y",  JSON_EXTRACT_SCALAR(json,  "$.clinical_study.completion_date.text")), INTERVAL 1 MONTH), INTERVAL 1 DAY)))
    ELSE (IF(REGEXP_CONTAINS(JSON_EXTRACT_SCALAR(json,
          "$.clinical_study.completion_date"), r"\d,"),
      PARSE_DATE("%B %e, %Y",
        JSON_EXTRACT_SCALAR(json,
          "$.clinical_study.completion_date")),
      DATE_SUB(DATE_ADD(PARSE_DATE("%B %Y",
            JSON_EXTRACT_SCALAR(json,
              "$.clinical_study.completion_date")), INTERVAL 1 MONTH), INTERVAL 1 DAY))) END AS completion_date,
  TRIM(json_EXTRACT(json,
      "$.clinical_study.study_design_info.primary_purpose"), '"') AS primary_purpose,
  TRIM(json_EXTRACT(json,
      "$.clinical_study.oversight_info.is_fda_regulated_drug"), '"') AS fda_reg_drug,
  TRIM(json_EXTRACT(json,
      "$.clinical_study.oversight_info.is_fda_regulated_device"), '"') AS fda_reg_device,
  TRIM(json_EXTRACT(json,
    "$.clinical_study.oversight_info.is_us_export"), '"') AS exported,
  json_EXTRACT(json,
    "$.clinical_study.location") AS study_location,
  PARSE_DATE("%B %e, %Y",
    JSON_EXTRACT_SCALAR(json,
      "$.clinical_study.results_first_submitted")) AS results_submitted_date,
  CASE
    WHEN json_EXTRACT(json,  "$.clinical_study.clinical_results") IS NOT NULL THEN 1
    ELSE 0
  END AS has_results,
  PARSE_DATE("%B %e, %Y",
    JSON_EXTRACT_SCALAR(json,
      "$.clinical_study.disposition_first_submitted")) AS certificate_date,
  TRIM(json_EXTRACT(json,
      "$.clinical_study.location_countries"), '"') AS location,
  TRIM(json_EXTRACT(json,
      "$.clinical_study.sponsors.lead_sponsor.agency"), '"') AS sponsor,
  TRIM(json_EXTRACT(json,
      "$.clinical_study.sponsors.lead_sponsor.agency_class"), '"') AS sponsor_type,
  CASE WHEN json_EXTRACT(json,
      "$.clinical_study.official_title") is null then
      TRIM(json_EXTRACT(json,
      "$.clinical_study.brief_title"), '"')
  ELSE TRIM(json_EXTRACT(json,
      "$.clinical_study.official_title"), '"') end AS title,
  TRIM(JSON_EXTRACT(json,
      "$.clinical_study.required_header.url"), '"') AS url,
  json_EXTRACT(json,
    "$.clinical_study.condition") AS condition,
  json_EXTRACT(json,
    "$.clinical_study.condition_browse") AS condition_mesh,
  json_EXTRACT(json,
    "$.clinical_study.intervention") AS intervention,
  json_EXTRACT(json,
    "$.clinical_study.intervention_browse") AS intervention_mesh
FROM
  clinicaltrials.clinicaltrials_json),

website_data AS (
 SELECT
  nct_id,
  CASE
    WHEN study_type = 'Interventional'
    AND (fda_reg_drug = 'Yes' OR fda_reg_device = 'Yes')
    AND (phase = 'Phase 1/Phase 2' OR phase = 'Phase 2' OR Phase = 'Phase 2/Phase 3' or phase = 'Phase 3' or phase = 'Phase 4' or phase = 'N/A')
    AND (primary_purpose <> 'Device Feasibility')
    AND (start_date >= '2017-01-18')
    AND study_status <> 'Withdrawn' THEN 1
    ELSE 0
  END AS act_flag,
  CASE
    WHEN study_type = 'Interventional'
    AND (regexp_contains(intervention, '"Biological"') OR regexp_contains(intervention, '"Drug"')
    OR regexp_contains(intervention, '"Device"') OR regexp_contains(intervention, '"Genetic"') OR regexp_contains(intervention, '"Radiation"'))
    AND (phase = 'Phase 1/Phase 2' OR phase = 'Phase 2' OR Phase = 'Phase 2/Phase 3' or phase = 'Phase 3' or phase = 'Phase 4' or phase = 'N/A')
    AND (available_completion_date >= '2017-01-18')
    AND (start_date < '2017-01-18')
    AND study_status <> 'Withdrawn'
    AND (regexp_contains(location, concat("\\b", "United States", "\\b"))
    OR regexp_contains(location, concat("\\b", "American Samoa", "\\b"))
    OR regexp_contains(location, concat("\\b", "Guam", "\\b"))
    OR regexp_contains(location, concat("\\b", "Northern Mariana Islands", "\\b"))
    OR regexp_contains(location, concat("\\b", "Puerto Rico", "\\b"))
    OR regexp_contains(location, concat("\\b", "U.S. Virgin Islands", "\\b")))
    THEN 1
    ELSE 0
  END AS included_pact_flag,
  location,
  exported,
  phase,
  start_date,
  available_completion_date,
  case when primary_completion_date is not null then 1 else 0 end as primary_completion_date_used,
  has_results,
  results_submitted_date,
  case when certificate_date is not null then 1 else 0 end as has_certificate,
  certificate_date,
  case when
   -- sets the deadline for results as 1 year + 30 days from completion date
  (Date_Add(Date_Add(available_completion_date, INTERVAL 1 YEAR), INTERVAL 30 DAY) < current_date())

    AND
    -- checks to see if it is an ACT
    (
    ((study_type = 'Interventional')
    AND (fda_reg_drug = 'Yes' OR fda_reg_device = 'Yes')
    AND (phase = 'Phase 1/Phase 2' OR phase = 'Phase 2' OR Phase = 'Phase 2/Phase 3' or phase = 'Phase 3' or phase = 'Phase 4' or phase = 'N/A')
    AND (primary_purpose <> 'Device Feasibility')
    AND (start_date >= '2017-01-18')
    AND (study_status <> 'Withdrawn'))

    OR
   -- checks to see if it's a pACT
   ((study_type = 'Interventional')
    AND (regexp_contains(intervention, '"Biological"') OR regexp_contains(intervention, '"Drug"')
    OR regexp_contains(intervention, '"Device"') OR regexp_contains(intervention, '"Genetic"') OR regexp_contains(intervention, '"Radiation"'))
    AND (phase = 'Phase 1/Phase 2' OR phase = 'Phase 2' OR Phase = 'Phase 2/Phase 3' or phase = 'Phase 3' or phase = 'Phase 4' or phase = 'N/A')
    AND (available_completion_date >= '2017-01-18')
    AND (start_date < '2017-01-18')
    AND (study_status <> 'Withdrawn')
    AND (regexp_contains(location, concat("\\b", "United States", "\\b"))
    OR regexp_contains(location, concat("\\b", "American Samoa", "\\b"))
    OR regexp_contains(location, concat("\\b", "Guam", "\\b"))
    OR regexp_contains(location, concat("\\b", "Northern Mariana Islands", "\\b"))
    OR regexp_contains(location, concat("\\b", "Puerto Rico", "\\b"))
    OR regexp_contains(location, concat("\\b", "U.S. Virgin Islands", "\\b"))))
    )
  -- checks to see if it has a certificate of exemption or if it's 3 years + 30 days after the primary completion date in which it's due no matter what
  AND (certificate_date is null OR (Date_ADD(Date_ADD(available_completion_date, Interval 3 YEAR), Interval 30 DAY) < current_date()))
  then 1 else 0 end as results_due,
  study_status,
  study_type,
  primary_purpose,
  fda_reg_drug,
  fda_reg_device,
  sponsor,
  sponsor_type,
  url,
  title,
  condition,
  condition_mesh,
  intervention,
  intervention_mesh
FROM
  full_data_extract)
SELECT * FROM website_data
WHERE
  included_pact_flag = 1 OR act_flag = 1
