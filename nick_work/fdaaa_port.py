import os
from bs4 import BeautifulSoup
import xmltodict
import json
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import csv
from collections import defaultdict
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

def is_covered_intervention(intervention_type):
    for it in intervention_type:
        if ('Drug' or 'Device' or 'Biological' or 'Genetic' or
           'Radiation' or 'Combination Prodcut' or 'Diagnostic Test') in it:
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
    if ('United States' or 'American Samoa' or 'Guam' or 
        'Northern Mariana Islands' or 'Puerto Rico' or 'Virgin Islands (U.S.)') in locs:
        return True
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

def dict_builder(your_dict,name,value):
    your_dict[name].append(value)
    return your_dict

effective_date = date(2017, 1, 18)
directory = 'NCTxxx' #this points to a folder on my working directory. Change as needed.

trial_dict = defaultdict(list)

for xml_filename in os.listdir(directory):
    with open(os.path.join(directory, xml_filename)) as raw_xml:
        soup = BeautifulSoup(raw_xml, 'xml')
    with open(os.path.join(directory, xml_filename), 'rb') as xml_to_json:
        parsed_json = xmltodict.parse(xml_to_json.read())
    
    nct_id = t(soup.nct_id)
    
    study_type = t(soup.study_type)
        
    has_certificate = does_it_exist(soup.disposition_first_submitted)

    phase = t(soup.phase)

    fda_reg_drug = t(soup.is_fda_regulated_drug)

    fda_reg_device = t(soup.is_fda_regulated_device)

    primary_purpose = t(soup.find('primary_purpose'))
    
    try:
        if fda_reg_dict[nct_id] == 'false':
            is_fda_regulated = False
        elif fda_reg_dict[nct_id] == 'true':
            is_fda_regulated = True
        else:
            is_fda_regulated = None
    except KeyError:
        is_fda_regulated = None
        
    study_status = t(soup.overall_status)

    start_date = (str_to_date(soup.start_date))[0]

    primary_completion_date, defaulted_pcd_flag = str_to_date(soup.primary_completion_date)

    completion_date, defaulted_cd_flag = str_to_date(soup.completion_date)
            
    if not primary_completion_date and not completion_date:
        available_completion_date = None
    elif completion_date and not primary_completion_date:
        available_completion_date = completion_date
        cd_flag = True
        used_primary_completion_date = False
    else:
        available_completion_date = primary_completion_date
        used_primary_completion_date = True
        cd_flag = False

    if (is_interventional(study_type) and
        is_fda_reg(fda_reg_drug, fda_reg_device) and
        is_covered_phase(phase) and
        is_not_device_feasibility(primary_purpose) and
        start_date >= effective_date and
        is_not_withdrawn(study_status)):
        act_flag = True
    else:
        act_flag = False
        
    intervention_type = soup.find_all("intervention_type")
    locs = t(soup.location_countries)

    if (is_interventional(study_type) and
        is_covered_intervention(intervention_type) and
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
        
    location = dict_or_none(parsed_json,[cs, 'location_countries'])

    has_results = does_it_exist(soup.results_first_submitted)
        
    pending_results = does_it_exist(soup.pending_results)


    pending_data = dict_or_none(parsed_json,[cs,'pending_results'])

    if ((act_flag == True or included_pact_flag == True) and
        date.today() > available_completion_date + relativedelta(years=1) + timedelta(days=30) and
        (has_certificate == 0 or (date.today() > available_completion_date + relativedelta(years=3) + timedelta(days=30)))):
        results_due = True
    else:
        results_due = False 
    
    results_submitted_date = (str_to_date(soup.results_first_submitted))[0]
    
    last_updated_date = (str_to_date(soup.last_update_submitted))[0]
    
    certificate_date = (str_to_date(soup.disposition_first_submitted))[0]

    enrollment = t(soup.enrollment)

    sponsor = t(soup.sponsors.lead_sponsor.agency)

    sponsor_type = t(soup.sponsors.lead_sponsor.agency_class)

    collaborators = dict_or_none(parsed_json, [cs, 'sponsors', 'collaborator'])  

    exported = t(soup.oversight_info.is_us_export)
        
    url = (soup.url).text
    
    official_title = t(soup.official_title)

    brief_title = t(soup.brief_title)

    if official_title is not None:
        title = official_title
    elif official_title is None and brief_title is not None:
        title = brief_title
    else:
        title = None

    #add this to "if" statement after testing: 'and completion_date is not null')
    if ((primary_completion_date < date.today() or primary_completion_date is None) and 
        completion_date < date.today() and study_status in ["Unknown status", "Active, not recruiting", "Not yet recruiting", 
                                                            "Enrolling by invitation", "Suspended", "Recruiting"]):
        discrep_date_status = True
    else:
        discrep_date_status = False
       
    if certificate_date is not None and certificate_date > (certificate_date + relativedelta(years=1)):
        late_cert = True
    else:
        late_cert = False
    
    if ((used_primary_completion_date == True and defaulted_pcd_flag == True) or 
        used_primary_completion_date == False and defaulted_cd_flag == True):
        defaulted_date = True
    else:
        defaulted_date = False
    
    condition = dict_or_none(parsed_json, [cs, 'condition'])
    
    condition_mesh = dict_or_none(parsed_json,[cs, 'condition_browse'])
        
    intervention = dict_or_none(parsed_json,[cs, 'intervention'])

    intervention_mesh = dict_or_none(parsed_json,[cs, 'intervention_browse'])
        
    keywords = dict_or_none(parsed_json,[cs, 'keyword'])
    
    dict_builder(trial_dict,'nct_id',nct_id)
    dict_builder(trial_dict,'act_flag',act_flag)
    dict_builder(trial_dict,'included_pact_flag',included_pact_flag)
    dict_builder(trial_dict,'has_results',has_results)
    dict_builder(trial_dict,'pending_results',pending_results)
    dict_builder(trial_dict,'pending_data',pending_data)
    dict_builder(trial_dict,'has_certificate',has_certificate)    
    dict_builder(trial_dict,'results_due',results_due)
    dict_builder(trial_dict,'start_date',start_date)    
    dict_builder(trial_dict,'available_completion_date',available_completion_date)
    dict_builder(trial_dict,'used_primary_completion_date',used_primary_completion_date)
    dict_builder(trial_dict,'defaulted_pcd_flag',defaulted_pcd_flag)
    dict_builder(trial_dict,'defaulted_cd_flag',defaulted_cd_flag)
    dict_builder(trial_dict,'results_submitted_date',results_submitted_date)
    dict_builder(trial_dict,'last_updated_date',last_updated_date)
    dict_builder(trial_dict,'certificate_date',certificate_date)
    dict_builder(trial_dict,'phase',phase)
    dict_builder(trial_dict,'enrollment',enrollment)
    dict_builder(trial_dict,'location',location)    
    dict_builder(trial_dict,'study_status',study_status)  
    dict_builder(trial_dict,'study_type',study_type)    
    dict_builder(trial_dict,'primary_purpose',primary_purpose)
    dict_builder(trial_dict,'sponsor', sponsor)
    dict_builder(trial_dict,'sponsor_type',sponsor_type)
    dict_builder(trial_dict,'collaborators',collaborators)  
    dict_builder(trial_dict,'exported',exported)
    dict_builder(trial_dict,'fda_reg_drug',fda_reg_drug)
    dict_builder(trial_dict,'fda_reg_device',fda_reg_device)
    dict_builder(trial_dict,'is_fda_regulated',is_fda_regulated)
    dict_builder(trial_dict,'url',url)
    dict_builder(trial_dict,'title',title)
    dict_builder(trial_dict,'official_title',official_title)    
    dict_builder(trial_dict,'brief_title',brief_title)
    dict_builder(trial_dict,'discrep_date_status',discrep_date_status)
    dict_builder(trial_dict,'late_cert',late_cert)
    dict_builder(trial_dict,'defaulted_date',defaulted_date)
    dict_builder(trial_dict,'condition',condition)
    dict_builder(trial_dict,'condition_mesh',condition_mesh)
    dict_builder(trial_dict,'intervention',intervention)
    dict_builder(trial_dict,'intervention_mesh',intervention_mesh)
    dict_builder(trial_dict,'keywords',keywords)
	
headers = trial_dict.keys()
with open('test_output.csv', 'w', newline='',encoding='utf-8') as test_csv:
    writer = csv.writer(test_csv)
    writer.writerow(headers)
    writer.writerows(zip(*trial_dict.values()))
