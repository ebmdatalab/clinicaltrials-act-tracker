import os
from bs4 import BeautifulSoup
import xmltodict
import json
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import csv
cs = 'clinical_study'

#when actually implemented, point this towards the static location of the file in the cloud
fda_reg_dict = {}
with open("fdaaa_regulatory_snapshot.csv") as old_fda_reg:
    reader = csv.DictReader(old_fda_reg)
    for d in reader:
        fda_reg_dict[d['nct_id']] = d['is_fda_regulated']


def is_covered_phase(phase):
    return phase in ['Phase 1/Phase 2', 'Phase 2', 'Phase 2/Phase 3' , 'Phase 3', 'Phase 4', 'N/A']

def is_not_withdrawn(study_status):
    return study_status != 'Withdrawn'

def is_interventional(study_type):
    return study_type == 'Interventional'

def is_covered_intervention(intervention_type_list):
    covered_intervention_type = ['Drug','Device','Biological','Genetic','Radiation','Combination Prodcut','Diagnostic Test']
    a_set = set(covered_intervention_type)
    b_set = set(intervention_type_list)
    if (a_set & b_set):
        return True
    else:
        return False

def is_not_device_feasibility(primary_purpose):
    return primary_purpose != 'Device Feasibility'

def is_fda_reg(fda_reg_drug, fda_reg_device):
    if fda_reg_drug == 'Yes' or fda_reg_device == 'Yes':
        return True
    else:
        return False

def is_old_fda_regulated(is_fda_regulated, fda_reg_drug, fda_reg_device):
    if ((fda_reg_drug is None and fda_reg_device is None) and
        is_fda_regulated is not False):
        return True
    else:
        return False
    
def has_us_loc(locs):
    us_locs = ['United States','American Samoa','Guam','Northern Mariana Islands','Puerto Rico','Virgin Islands (U.S.)']
    for us_loc in us_locs:
        if us_loc in locs:
            return True
            break
        else:
            return False
    
def dict_or_none(data, keys):
    for k in keys:
        try:
            data = data[k]
        except KeyError:
            return None
    return json.dumps(data)

#Some dates on clinicaltrials.gov are only Month-Year not Day-Month-Year. 
#When this happens, we assign them to the last day of the month so our "results due" assessments are conservative
def str_to_date(datestr):
    is_defaulted_date = False
    if datestr is not None:   
        try:
            parsed_date = datetime.strptime(datestr.text, '%B %d, %Y').date()
        except ValueError:
            parsed_date = datetime.strptime(datestr.text, '%B %Y').date() + relativedelta(months=+1) - timedelta(days=1)
            is_defaulted_date = True
    else:
        parsed_date = None
    return (parsed_date, is_defaulted_date)

def t(textish):
    if textish is None:
        return None
    return textish.text

def does_it_exist(dataloc):
    if dataloc is None:
        return False
    else:
        return True

headers = ['nct_id', 'act_flag', 'included_pact_flag', 'has_results', 'pending_results', 'pending_data',
           'has_certificate', 'results_due', 'start_date', 'available_completion_date',
           'used_primary_completion_date', 'defaulted_pcd_flag', 'defaulted_cd_flag', 'results_submitted_date',
           'last_updated_date', 'certificate_date', 'phase', 'enrollment', 'location', 'study_status', 'study_type',
           'primary_purpose', 'sponsor', 'sponsor_type', 'collaborators', 'exported', 'fda_reg_drug',
           'fda_reg_device', 'is_fda_regulated', 'url', 'title', 'official_title', 'brief_title',
           'discrep_date_status', 'late_cert', 'defaulted_date', 'condition', 'condition_mesh', 'intervention',
           'intervention_mesh', 'keywords']

effective_date = date(2017, 1, 18)
directory = 'NCTxxx' #this points to a folder in my working directory. Change as needed.

trial_dict = defaultdict(list)

with open('test_output.csv', 'w', newline='',encoding='utf-8') as test_csv:
    writer = csv.DictWriter(test_csv, fieldnames=headers)
    writer.writeheader()

    for xml_filename in os.listdir(directory):
        if xml_filename.endswith('.xml'): #had to keep this because of hidden file OSX funky-ness 
            with open(os.path.join(directory, xml_filename)) as raw_xml:
                soup = BeautifulSoup(raw_xml, 'xml')
            with open(os.path.join(directory, xml_filename), 'rb') as xml_to_json:
                parsed_json = xmltodict.parse(xml_to_json.read())

            td = {}

            nct_id = t(soup.nct_id)
            td['nct_id'] = nct_id

            study_type = t(soup.study_type)
            td['study_type'] = study_type

            has_certificate = does_it_exist(soup.disposition_first_submitted)
            td['has_certificate'] = has_certificate

            phase = t(soup.phase)
            td['phase'] = phase

            fda_reg_drug = t(soup.is_fda_regulated_drug)
            td['fda_reg_drug'] = fda_reg_drug

            fda_reg_device = t(soup.is_fda_regulated_device)
            td['fda_reg_device'] = fda_reg_device

            primary_purpose = t(soup.find('primary_purpose'))
            td['primary_purpose'] = primary_purpose

            try:
                if fda_reg_dict[nct_id] == 'false':
                    is_fda_regulated = False
                elif fda_reg_dict[nct_id] == 'true':
                    is_fda_regulated = True
                else:
                    is_fda_regulated = None
            except KeyError:
                is_fda_regulated = None
            td['is_fda_regulated'] = is_fda_regulated

            study_status = t(soup.overall_status)
            td['study_status'] = study_status

            start_date = (str_to_date(soup.start_date))[0]
            td['start_date'] = start_date

            primary_completion_date, defaulted_pcd_flag = str_to_date(soup.primary_completion_date)
            td['defaulted_pcd_flag'] = defaulted_pcd_flag

            completion_date, defaulted_cd_flag = str_to_date(soup.completion_date)
            td['defaulted_cd_flag'] = defaulted_cd_flag

            if not primary_completion_date and not completion_date:
                available_completion_date = None
            elif completion_date and not primary_completion_date:
                available_completion_date = completion_date
                used_primary_completion_date = False
            else:
                available_completion_date = primary_completion_date
                used_primary_completion_date = True
            td['available_completion_date'] = available_completion_date
            td['used_primary_completion_date'] = used_primary_completion_date

            if (is_interventional(study_type) and
                is_fda_reg(fda_reg_drug, fda_reg_device) and
                is_covered_phase(phase) and
                is_not_device_feasibility(primary_purpose) and
                start_date >= effective_date and
                is_not_withdrawn(study_status)):
                act_flag = True
            else:
                act_flag = False
            td['act_flag'] = act_flag

            intervention_type_field = soup.find_all("intervention_type")
            trial_intervention_types = []
            for tag in intervention_type_field:
                trial_intervention_types.append(tag.get_text())
            
            locs = t(soup.location_countries)

            if (is_interventional(study_type) and
                is_covered_intervention(trial_intervention_types) and
                is_covered_phase(phase) and
                is_not_device_feasibility(primary_purpose) and
                available_completion_date >= effective_date and
                start_date < effective_date and
                is_not_withdrawn(study_status) and
                (is_fda_reg(fda_reg_drug, fda_reg_device) or
                 is_old_fda_regulated(is_fda_regulated, fda_reg_drug, fda_reg_device)) and
                has_us_loc(locs)):
                old_pact_flag = True
            else:
                old_pact_flag = False

            if (is_interventional(study_type) and
                is_fda_reg(fda_reg_drug, fda_reg_device) and
                is_covered_phase(phase) and
                is_not_device_feasibility(primary_purpose) and
                start_date < effective_date and
                available_completion_date >= effective_date and
                is_not_withdrawn(study_status)):
                new_pact_flag = True
            else:
                new_pact_flag = False

            if old_pact_flag == True or new_pact_flag == True:
                included_pact_flag = True
            else:
                included_pact_flag = False
            td['included_pact_flag'] = included_pact_flag

            td['location'] = dict_or_none(parsed_json,[cs, 'location_countries'])

            td['has_results'] = does_it_exist(soup.results_first_submitted)

            td['pending_results'] = does_it_exist(soup.pending_results)

            td['pending_data'] = dict_or_none(parsed_json,[cs,'pending_results'])

            if ((act_flag == True or included_pact_flag == True) and
                date.today() > available_completion_date + relativedelta(years=1) + timedelta(days=30) and
                (has_certificate == 0 or (date.today() > available_completion_date + relativedelta(years=3) + timedelta(days=30)))):
                td['results_due'] = True
            else:
                td['results_due'] = False 

            td['results_submitted_date'] = (str_to_date(soup.results_first_submitted))[0]

            td['last_updated_date'] = (str_to_date(soup.last_update_submitted))[0]

            certificate_date = (str_to_date(soup.disposition_first_submitted))[0]
            td['certificate_date'] = certificate_date

            td['enrollment'] = t(soup.enrollment)

            td['sponsor'] = t(soup.sponsors.lead_sponsor.agency)

            td['sponsor_type'] = t(soup.sponsors.lead_sponsor.agency_class)

            td['collaborators'] = dict_or_none(parsed_json, [cs, 'sponsors', 'collaborator'])  

            td['exported'] = t(soup.oversight_info.is_us_export)

            td['url'] = (soup.url).text

            official_title = t(soup.official_title)
            td['official_title'] = official_title

            brief_title = t(soup.brief_title)
            td['brief_title'] = brief_title

            if official_title is not None:
                td['title'] = official_title
            elif official_title is None and brief_title is not None:
                td['title'] = brief_title
            else:
                td['title'] = None

            #add this to "if" statement after testing: 'and completion_date is not null')
            if ((primary_completion_date < date.today() or primary_completion_date is None) and 
                completion_date < date.today() and study_status in ["Unknown status", "Active, not recruiting", "Not yet recruiting", 
                                                                    "Enrolling by invitation", "Suspended", "Recruiting"]):
                td['discrep_date_status'] = True
            else:
                td['discrep_date_status'] = False

            if certificate_date is not None and certificate_date > (certificate_date + relativedelta(years=1)):
                td['late_cert'] = True
            else:
                td['late_cert'] = False

            if ((used_primary_completion_date == True and defaulted_pcd_flag == True) or 
                used_primary_completion_date == False and defaulted_cd_flag == True):
                td['defaulted_date'] = True
            else:
                td['defaulted_date'] = False

            td['condition'] = dict_or_none(parsed_json, [cs, 'condition'])

            td['condition_mesh'] = dict_or_none(parsed_json,[cs, 'condition_browse'])

            td['intervention'] = dict_or_none(parsed_json,[cs, 'intervention'])

            td['intervention_mesh'] = dict_or_none(parsed_json,[cs, 'intervention_browse'])

            td['keywords'] = dict_or_none(parsed_json,[cs, 'keyword'])

            writer.writerow(td)
