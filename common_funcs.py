#
#  NOTE - please change this to match the database for use.
#

def get_criteria_type_map():
    d = {
        'biomarker_exc' : 1,
        'biomarker_inc' : 2,
        'hiv_exc' : 5,
        'plt': 6,
        'wbc': 7,
        'perf': 8,
        'bmets': 11,
        'pt_inc': 12,
        'pt_exc': 18,
        'disease_inc' : 19 
    }
    return d
