-- Takes a JSON dump of clinicaltrials.gov in BigQuery and turns it to
-- a tabular format which includes fields necessary to identify ACTs
-- and their lateness (or otherwise)
--
-- The logic is documented here: https://github.com/ebmdatalab/clinicaltrials-act-tracker/issues/2#issuecomment-358318279

WITH full_data_extract AS (
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
  Case when JSON_EXTRACT(json, "$.clinical_study.primary_completion_date.text") IS NOT NULL then 1 else 0 end as used_primary_completion_date,
  IF(REGEXP_CONTAINS(JSON_EXTRACT_SCALAR(json,
        "$.clinical_study.primary_completion_date.text"), r"\d,"),
    PARSE_DATE("%B %e, %Y",
      JSON_EXTRACT_SCALAR(json,
        "$.clinical_study.primary_completion_date.text")),
    DATE_SUB(DATE_ADD(PARSE_DATE("%B %Y",
          JSON_EXTRACT_SCALAR(json,
            "$.clinical_study.primary_completion_date.text")), INTERVAL 1 MONTH), INTERVAL 1 DAY)) AS primary_completion_date,
  Case when (REGEXP_CONTAINS(JSON_EXTRACT_SCALAR(json, "$.clinical_study.primary_completion_date.text"),
      r"\d,") OR (JSON_EXTRACT(json, "$.clinical_study.primary_completion_date.text") is null)) then 0 else 1 end as defaulted_pcd_flag,           
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
 Case when 
(REGEXP_CONTAINS(JSON_EXTRACT_SCALAR(json, "$.clinical_study.completion_date.text"),
      r"\d,") OR REGEXP_CONTAINS(JSON_EXTRACT_SCALAR(json, "$.clinical_study.completion_date"),
      r"\d,") OR (JSON_EXTRACT_SCALAR(json, "$.clinical_study.completion_date.text") is null AND JSON_EXTRACT_SCALAR(json, "$.clinical_study.completion_date") is null))
      then 0 else 1 end as defaulted_cd_flag,            
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
  PARSE_DATE("%B %e, %Y",
    JSON_EXTRACT_SCALAR(json,
      "$.clinical_study.last_update_submitted")) AS last_updated_date,    
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
  TRIM(json_extract(json, "$.clinical_study.sponsors.collaborator"), '"') AS collaborators,    
  TRIM(case when (json_extract(json, "$.clinical_study.enrollment.text")) is not null then  
  (json_extract(json,
      "$.clinical_study.enrollment.text")) else (json_extract(json, "$.clinical_study.enrollment")) end, '"') AS enrollment,
  CASE WHEN json_EXTRACT(json,
      "$.clinical_study.official_title") is null then 
      TRIM(json_EXTRACT(json,
      "$.clinical_study.brief_title"), '"')
  ELSE TRIM(json_EXTRACT(json,
      "$.clinical_study.official_title"), '"') end AS title,
  TRIM(JSON_Extract(json,
      "$.clinical_study.official_title"),'"') as official_title,
  TRIM(JSON_Extract(json,
      "$.clinical_study.brief_title"),'"') as brief_title,
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
   ebmdatalab.clinicaltrials.current_raw_json),

website_data AS (
 SELECT
  full_data_extract.nct_id,
  
  /*Creating the flag for an ACT*/
  CASE
    WHEN study_type = 'Interventional' 
    AND (fda_reg_drug = 'Yes' OR fda_reg_device = 'Yes')
    AND (phase = 'Phase 1/Phase 2' OR phase = 'Phase 2' OR Phase = 'Phase 2/Phase 3' or phase = 'Phase 3' or phase = 'Phase 4' or phase = 'N/A') 
    AND (primary_purpose <> 'Device Feasibility')
    AND (start_date >= '2017-01-18') 
    AND study_status <> 'Withdrawn' THEN 1
    ELSE 0
  END AS act_flag,
  
/*Creating the Flag for a pACT*/
  CASE
    WHEN study_type = 'Interventional'
    AND (regexp_contains(intervention, '"Biological"') OR regexp_contains(intervention, '"Drug"') 
    OR regexp_contains(intervention, '"Device"') OR regexp_contains(intervention, '"Genetic"') OR regexp_contains(intervention, '"Radiation"') OR regexp_contains(intervention, '"Combination Product"') OR regexp_contains(intervention, '"Diagnostic Test"'))
    AND (phase = 'Phase 1/Phase 2' OR phase = 'Phase 2' OR Phase = 'Phase 2/Phase 3' or phase = 'Phase 3' or phase = 'Phase 4' or phase = 'N/A') 
    AND (primary_purpose <> 'Device Feasibility')
    AND (available_completion_date >= '2017-01-18')
    AND (start_date < '2017-01-18')
    AND study_status <> 'Withdrawn' 
    AND (
          (fda_reg_drug = 'Yes' OR fda_reg_device = 'Yes')
        OR
          (is_fda_regulated IS NOT FALSE
            AND fda_reg_drug IS NULL
            AND fda_reg_device IS NULL)
            ) -- for trials which were pACTs and the sponsor subsequently updated. See #92.
    AND (regexp_contains(location, concat("\\b", "United States", "\\b"))
    OR regexp_contains(location, concat("\\b", "American Samoa", "\\b"))  
    OR regexp_contains(location, concat("\\b", "Guam", "\\b")) 
    OR regexp_contains(location, concat("\\b", "Northern Mariana Islands", "\\b"))
    OR regexp_contains(location, concat("\\b", "Puerto Rico", "\\b"))
    OR regexp_contains(location, concat("\\b", "U.S. Virgin Islands", "\\b")))
    THEN 1
    ELSE 0
  END AS included_pact_flag,
  
/*Results Related Info*/
  has_results,
  case when certificate_date is not null then 1 else 0 end as has_certificate,
  case when 
  --Steps for determining if results are due
  --Sets the deadline for results as 1 year + 30 days from completion date
  (Date_Add(Date_Add(available_completion_date, INTERVAL 1 YEAR), INTERVAL 30 DAY) < current_date()) 
    
    AND 
    --checks to see if it is an ACT
    (
    ((study_type = 'Interventional')
    AND (fda_reg_drug = 'Yes' OR fda_reg_device = 'Yes')
    AND (phase = 'Phase 1/Phase 2' OR phase = 'Phase 2' OR Phase = 'Phase 2/Phase 3' or phase = 'Phase 3' or phase = 'Phase 4' or phase = 'N/A') 
    AND (primary_purpose <> 'Device Feasibility')
    AND (start_date >= '2017-01-18') 
    AND (study_status <> 'Withdrawn'))
    
    OR
   --checks to see if it's a pACT
   ((study_type = 'Interventional')
    AND (regexp_contains(intervention, '"Biological"') OR regexp_contains(intervention, '"Drug"') 
    OR regexp_contains(intervention, '"Device"') OR regexp_contains(intervention, '"Genetic"') OR regexp_contains(intervention, '"Radiation"') OR regexp_contains(intervention, '"Combination Product"') OR regexp_contains(intervention, '"Diagnostic Test"'))
    AND (phase = 'Phase 1/Phase 2' OR phase = 'Phase 2' OR Phase = 'Phase 2/Phase 3' or phase = 'Phase 3' or phase = 'Phase 4' or phase = 'N/A') 
    AND (primary_purpose <> 'Device Feasibility')
    AND (available_completion_date >= '2017-01-18') 
    AND (start_date < '2017-01-18')
    AND (study_status <> 'Withdrawn') 
    AND (
          (fda_reg_drug = 'Yes' OR fda_reg_device = 'Yes')
        OR
          (is_fda_regulated IS NOT FALSE
            AND fda_reg_drug IS NULL
            AND fda_reg_device IS NULL)
            ) -- for trials which were pACTs and the sponsor subsequently updated. See #92.
    AND (regexp_contains(location, concat("\\b", "United States", "\\b"))
    OR regexp_contains(location, concat("\\b", "American Samoa", "\\b"))  
    OR regexp_contains(location, concat("\\b", "Guam", "\\b")) 
    OR regexp_contains(location, concat("\\b", "Northern Mariana Islands", "\\b"))
    OR regexp_contains(location, concat("\\b", "Puerto Rico", "\\b"))
    OR regexp_contains(location, concat("\\b", "U.S. Virgin Islands", "\\b")))) 
    )
  --checks to see if it has a certificate of exemption or if it's 3 years + 30 days after the primary completion date in which it's due no matter what  
  AND (certificate_date is null OR (Date_ADD(Date_ADD(available_completion_date, Interval 3 YEAR), Interval 30 DAY) < current_date()))
  then 1 else 0 end as results_due, 
  
  
/*Key Dates and Date Info*/
  start_date,
  available_completion_date, --PCD if available, if not available, uses completion date
  used_primary_completion_date, --IF 1, tells you that "available_completion-date" used PCD
  defaulted_pcd_flag, --If 1, tells you PCD did not have a date and was defaulted to the end of the month
  defaulted_cd_flag, --If 1, tells you CD did not have a date and was defaulted to the end of the month
  results_submitted_date, --The day results information was submitted by sponsor. Doesn't appear in XML until results are posted. Use webscraped value for this field when applicable.
  last_updated_date, --The last date the trial record was updated
  certificate_date, --The date the sponsor submitted their request for a certificate of delay or an extension

/*General Trial Info*/  
  phase,
  enrollment,
  location,
  study_status,
  study_type,
  primary_purpose,
 
/*Trial Sponsor Info*/
  sponsor,
  sponsor_type,
  collaborators, --This field contains an array with any collaborators and their "type"
  
/*Regulatory Info*/  
  exported,
  fda_reg_drug,
  fda_reg_device,
  is_fda_regulated,

/*Additional Trial Info for Website*/  
  url,
  title, --This uses "official_title" when available, otherwise it uses "brief_title"
  official_title,
  brief_title, --This is what appears as the headline trial title on ClinicalTrials.gov
  
/*"Bad Data" checks*/  
  --This checks to see if both the primary completion date and the completion date have passed but the trial still has an "ongoing" trial status
  CASE
    WHEN ((primary_completion_date < CURRENT_DATE() OR primary_completion_date IS NULL) AND completion_date < CURRENT_DATE() AND study_status IN ('Not yet recruiting',  'Active, not recruiting',  'Recruiting',  'Enrolling by invitation',  'Unknown status',  'Available',  'Suspended')) THEN 1
    ELSE 0
  END AS discrep_date_status,
  
  --This checks to see if a certificate of delay or an extension was applied for after the trial was otherwise due to report results (w/o 30 day buffer) which is not allowed per the Final Rule
  --We only care about this for pACTs/ACTs
  CASE
    WHEN certificate_date > (DATE_ADD(DATE_ADD(available_completion_date, INTERVAL 1 YEAR), INTERVAL 30 DAY)) THEN 1
    ELSE 0
  END AS late_cert,
  
  --This is a flag for when the date we use for "available_completion_date" has been defaulted to the end of the month
  CASE
    WHEN (used_primary_completion_date = 1 and defaulted_pcd_flag = 1) OR (used_primary_completion_date = 0 and defaulted_cd_flag = 1) THEN 1
    ELSE 0
  END AS defaulted_date,

/*Will be used in future to inform Trial search*/ 
  condition,
  condition_mesh,
  intervention,
  intervention_mesh
FROM
  full_data_extract
LEFT JOIN
  ebmdatalab.clinicaltrials.jan17_fda_regulation_snapshot
ON
  jan17_fda_regulation_snapshot.nct_id = full_data_extract.nct_id
)
SELECT * FROM website_data
WHERE
  included_pact_flag = 1 OR act_flag = 1
