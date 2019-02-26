import os
from bs4 import BeautifulSoup
import xmltodict
import json
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import pandas as pd
import csv
cs = 'clinical_study'

projectid = "ebmdatalab"

fda_reg_df = pd.read_gbq('''
SELECT *
FROM clinicaltrials.jan17_fda_regulation_snapshot 
''', projectid, dialect = 'standard')

headers = ['nct_id', 'act_flag', 'included_pact_flag', 'has_results', 'pending_results', 'pending_data',\
           'has_certificate', 'results_due', 'start_date', 'available_completion_date',\
           'used_primary_completion_date', 'defaulted_pcd_flag', 'defaulted_cd_flag', 'results_submitted_date',\
           'last_updated_date', 'certificate_date', 'phase', 'enrollment', 'location', 'study_status', 'study_type',\
           'primary_purpose', 'sponsor', 'sponsor_type', 'collaborators', 'exported', 'fda_reg_drug',\
           'fda_reg_device', 'is_fda_regulated', 'url', 'title', 'official_title', 'brief_title',\
           'discrep_date_status', 'late_cert', ' defaulted_date', 'condition', 'condition_mesh', 'intervention',\
           'intervention_mesh', 'keywords']

effective_date = date(2017, 1, 18)
directory = 'NCTxxx' #this points to a folder on my working directory. Change as needed.

with open('test_output.csv', 'w') as test_csv:
    writer = csv.writer(test_csv)
    writer.writerow(headers)

    for file in os.listdir(directory):
        if file.endswith('.xml'):
            xml_bs4 = open(directory + '/' + file)
            xml_contents = xml_bs4.read()
            soup = BeautifulSoup(xml_contents,'xml')
            xml_json = open(directory + '/' + file, 'rb')
            parsed_json = xmltodict.parse(xml_json.read())

            #nct_id
            nct_id = (soup.nct_id).text

            #study_type
            study_type = (soup.study_type).text

            #has_certificate
            hc = soup.disposition_first_submitted
            if hc is not None:
                has_certificate = 1
            else:
                has_certificate = 0

            #phase
            phase = (soup.phase).text    

            #fda_reg_drug
            if soup.is_fda_regulated_drug is None:
                fda_reg_drug = None
            else:
                fda_reg_drug = (soup.is_fda_regulated_drug).text

            #fda_reg_device
            if soup.is_fda_regulated_device is None:
                fda_reg_device = None
            else:
                fda_reg_device = (soup.is_fda_regulated_device).text

            #primary_purpose
            if soup.find('primary_purpose') is not None:
                primary_purpose = soup.find('primary_purpose').text
            else:
                primary_purpose = None

            #is_fda_regulated
            df_row = fda_reg_df.loc[fda_reg_df['nct_id'] == nct_id]
            if df_row.empty:
                is_fda_regulated = None
            else:
                is_fda_regulated = df_row['is_fda_regulated'].values[0]

            #study_status
            study_status = (soup.overall_status).text

            #start_date
            sd = soup.start_date
            if sd is not None:
                try:
                    start_date = datetime.strptime(sd.text, '%B %d, %Y').date()
                except ValueError:
                    start_date = datetime.strptime(sd.text, '%B %Y').date() + relativedelta(months=+1) - timedelta(days=1)
            else:
                start_date = None

            #available_completion_date
            pcd = soup.primary_completion_date
            if pcd is not None:
                try:
                    primary_completion_date = datetime.strptime(pcd.text, '%B %d, %Y').date()
                    defaulted_pcd = 0
                except ValueError:
                    primary_completion_date = datetime.strptime(pcd.text, '%B %Y').date() + relativedelta(months=+1) - timedelta(days=1)
                    defaulted_pcd = 1
            else:
                primary_completion_date = None
                defaulted_pcd = 0

            cd = soup.completion_date
            if cd is not None:
                try:
                    completion_date = datetime.strptime(cd.text, '%B %d, %Y').date()
                    defaulted_cd = 0
                except ValueError:
                    completion_date = datetime.strptime(cd.text, '%B %Y').date() + relativedelta(months=+1) - timedelta(days=1)
                    defaulted_cd = 1
            else:
                completion_date = None
                defaulted_cd = 0

            if primary_completion_date == None and completion_date == None:
                available_completion_date = None
            elif primary_completion_date == None and completion_date is not None:
                available_completion_date = completion_date
                used_cd = 1
                used_pcd = 0
            else:
                available_completion_date = primary_completion_date
                used_pcd = 1
                used_cd = 0

            #act_flag - #looks like != handles nulls in Python so no need for extra term we use in BQ
            if study_type == 'Interventional' and\
            (fda_reg_drug == 'Yes' or fda_reg_device == 'Yes') and\
            (
             phase == 'Phase 1/Phase 2' or phase == 'Phase 2' or\
             phase == 'Phase 2/Phase 3' or phase == 'Phase 3' or\
             phase == 'Phase 4' or phase == 'N/A'
            ) and\
            primary_purpose != 'Device Feasibility' and\
            start_date >= effective_date and\
            study_status != 'Withdrawn':
                act_flag = 1
            else:
                act_flag = 0

            #included_pact_flag
            #Learned during this exercise - we need to change "U.S. Virgin Islands" to "Virgin Islands (U.S.)"
            #Can either leave here and compare to currnet SQL or correct the SQL first and then compare
            for it in soup.find_all("intervention_type"):
                if ('Drug' or 'Device' or 'Biological' or 'Genetic' or\
                'Radiation' or 'Combination Product' or 'Diagnostic Test') in it:
                    incl_it = 1
                    break
                else:
                    incl_it = 0
            locs = (soup.location_countries).text
            if study_type == 'Interventional' and\
            incl_it == 1 and\
            (
             phase == 'Phase 1/Phase 2' or phase == 'Phase 2' or\
             phase == 'Phase 2/Phase 3' or phase == 'Phase 3' or\
             phase == 'Phase 4' or phase == 'N/A'
            ) and\
            primary_purpose != 'Device Feasibility' and\
            available_completion_date >= effective_date and\
            start_date < effective_date and\
            study_status != 'Withdrawn' and\
            (
                (fda_reg_drug == 'Yes' or fda_reg_device == 'Yes')
                or
                (is_fda_regulated is not False and\
                 fda_reg_drug is None and fda_reg_device is None)
            ) and\
            (
             ('United States' or 'American Samoa' or 'Guam' or\
             'Northern Mariana Islands' or 'Puerto Rico' or 'U.S. Virgin Islands') in locs
            ):
                included_pact_flag = 1
            else:
                included_pact_flag = 0

            #location
            try:
                location = json.dumps(parsed_json['clinical_study']['location_countries'])
            except KeyError:
                location = None

            #has_results
            rsd = soup.results_first_submitted
            if rsd is not None:
                has_results = 1
            else:
                has_results = 0

            #pending_results
            pr = soup.pending_results
            if pr is not None:
                pending_results = 1
            else:
                pending_results = 0

            #pending_data -- Need XML with this to test
            try:
                pending_data = json.dumps(parsed_json['clinical_study']['pending_results'])
            except KeyError:
                pending_data = None

            #results_due
            if (act_flag == 1 or included_pact_flag == 1) and\
            date.today() > available_completion_date + relativedelta(years=1) + timedelta(days=30) and\
            (has_certificate == 0 or\
            (date.today() > available_completion_date + relativedelta(years=3) + timedelta(days=30))):
                results_due = 1
            else:
                results_due = 0

            #used_primary_completion_date
            used_primary_completion_date = used_pcd

            #defaulted_pcd_flag
            defaulted_pcd_flag = defaulted_pcd

            #cd_flag
            cd_flag = used_cd

            #defaulted_cd_flag
            defaulted_cd_flag = defaulted_cd

            #results_submitted_date
            if rsd is not None:
                results_submitted_date = datetime.strptime(soup.find('results_first_submitted').text, '%B %d, %Y').date()
            else:
                results_submitted_date = None

            #last_updated_date 
            lud = (soup.last_update_submitted).text
            last_updated_date = datetime.strptime(lud, '%B %d, %Y').date()

            #certificate_date
            if hc is not None:
                certificate_date = datetime.strptime(hc.text, '%B %d, %Y').date()
            else:
                certificate_date = None

            #enrollment
            enrollment = (soup.enrollment).text

            #sponsor
            sponsor = (soup.sponsors.lead_sponsor.agency).text

            #sponsor_type
            sponsor_type = (soup.sponsors.lead_sponsor.agency_class).text

            #collaborators
            try:
                collaborators = json.dumps(parsed_json['clinical_study']['sponsors']['collaborator'])
            except KeyError:
                collaborators = None

            #exported
            if soup.oversight_info.is_us_export is not None:
                exported = (soup.oversight_info.is_us_export).text
            else:
                exported = None

            #url
            url = (soup.url).text

            #official_title
            if soup.official_title is None:
                official_title = None
            else:
                official_title = (soup.official_title).text

            #brief_title
            if soup.brief_title is None:
                brief_title = None
            else:
                brief_title = (soup.brief_title).txt

            #title
            if official_title is not None:
                title = official_title
            elif official_title is None and brief_title is not None:
                title = brief_title
            else:
                title = None

            #discrep_date_status - add this to "if" statement after testing: 'and completion_date is not null')
            if (primary_completion_date < date.today() or primary_completion_date is None) and\
            completion_date < date.today() and\
            study_status is ("Unknown status" or "Active, not recruiting" or "Not yet recruiting" or\
            "Enrolling by invitation" or "Suspended" or "Recruiting"):
                discrep_date_status = 1
            else:
                discrep_date_status = 0

            #late_cert
            if certificate_date is not None and certificate_date > (certificate_date + relativedelta(years=1)):
                late_cert = 1
            else:
                late_cert = 0

            #defaulted_date
            if (used_primary_completion_date == 1 and defaulted_pcd_flag == 1) or\
            used_primary_completion_date == 0 and defaulted_cd_flag == 1:
                defaulted_date = 1
            else:
                defaulted_date = 0

            #condition
            try:
                condition = json.dumps(parsed_json['clinical_study']['condition'])
            except KeyError:
                condition = None

            #condition_mesh
            try:
                condition_mesh = json.dumps(parsed_json['clinical_study']['condition_browse'])
            except KeyError:
                condition_mesh = None

            #intervention
            try:
                intervention = json.dumps(parsed_json['clinical_study']['intervention'])
            except KeyError:
                intervention = None

            #intervention_mesh
            try:
                intervention_mesh = json.dumps(parsed_json['clinical_study']['intervention_browse'])
            except KeyError:
                intervention_mesh = None

            #keywords
            try:
                keywords = json.dumps(parsed_json['clinical_study']['keyword'])
            except KeyError:
                keywords = None

            row_list = [nct_id, act_flag, included_pact_flag, has_results, pending_results, pending_data, has_certificate,\
                       results_due, start_date, available_completion_date, used_primary_completion_date, defaulted_pcd_flag,\
                       defaulted_cd_flag, results_submitted_date, last_updated_date, certificate_date, phase, enrollment,\
                       location, study_status, study_type, primary_purpose, sponsor, sponsor_type, collaborators, exported,\
                       fda_reg_drug, fda_reg_device, is_fda_regulated, url, title, official_title, brief_title,\
                       discrep_date_status, late_cert, defaulted_date, condition, condition_mesh, intervention, intervention_mesh,\
                       keywords]

            writer.writerow(row_list)
