#!/usr/bin/env python
"""Python script to download and evaluate session 3 and 4 homeworks of data management sessions in the Biostatistics
course of the Master of Global Health of ISGlobal."""
import pandas
import redcap
import tokens

from sqlalchemy import create_engine

__author__ = "Maximo Ramirez Robles"
__copyright__ = "Copyright 2020, ISGlobal MHG2020"
__credits__ = ["Maximo Ramirez Robles"]
__license__ = "MIT"
__version__ = "0.0.1"
__date__ = "20201029"
__maintainer__ = "Maximo Ramirez Robles"
__email__ = "maximo.ramirez@isglobal.org"
__status__ = "Dev"


def get_data_dictionary(url, token):
    """Retrieve from the REDCap the list of field names in the project data dictionary.

    :param url: The URL of the REDCap API
    :type url: str
    :param token: The token for authentication in the REDCap API
    :type token: str
    :return: List of field names in the project data dictionary
    :rtype: list
    """
    project = redcap.Project(url, token)
    dic = project.export_metadata()

    field_names = []
    for field in dic:
        field_names.append(field['field_name'])
    return field_names


def get_project_id(url, token):
    """Retrieve from the REDCap the id of the project.

    :param url: The URL of the REDCap API
    :type url: str
    :param token: The token for authentication in the REDCap API
    :type token: str
    :return: The id of the project
    :rtype: int
    """
    project = redcap.Project(url, token)
    info = project.export_project_info()

    return info['project_id']


def get_project_name(url, token):
    """Retrieve from the REDCap the name of the project.

    :param url: The URL of the REDCap API
    :type url: str
    :param token: The token for authentication in the REDCap API
    :type token: str
    :return: The name of the project
    :rtype: str
    """
    project = redcap.Project(url, token)
    info = project.export_project_info()

    return info['project_title']


def get_number_of_records(url, token):
    """Retrieve from the REDCap the number of records created in a project.

    :param url: The URL of the REDCap API
    :type url: str
    :param token: The token for authentication in the REDCap API
    :type token: str
    :return: Number of records in the project
    :rtype: int
    """
    project = redcap.Project(url, token)
    records = project.export_records()

    return len(records)


def compute_completion_pct(master_data_dic, student_data_dic):
    """Get fields from student data dictionary that are correctly designed. Correctly designed means have the same
    field name (evaluation method MGH2020).

    :param master_data_dic: The list of field names that represents the exercise correct solution
    :type master_data_dic: list
    :param student_data_dic: The fist of field names that represents the student proposed solution
    :type student_data_dic: list
    :return: Percentage number of correct fields of the student proposed solution
    :rtype: float
    """
    correct_fields = set(master_data_dic) & set(student_data_dic)

    return len(correct_fields) / len(master_data_dic)


def download_data_dictionary(url, token):
    """Download and store the student data dictionary in the downloads folder.

    :param url: The URL of the REDCap API
    :type url: str
    :param token: The token for authentication in the REDCap API
    :type token: str
    :return: None
    """
    project = redcap.Project(url, token)
    dic = project.export_metadata(format='csv')

    project_name = get_project_name(url, token)
    filename = "downloads/" + project_name + ".csv"
    with open(filename, 'w', newline='') as file:
        file.write(dic)


def compute_student_performance(url, token):
    """For each student the following performance indicators will be computed:
        - Number of fields the student designed in her project.
        - Completion percentage, i.e. number of fields designed by the student divided by the total number of fields in
          the master solution.
        - Number of records created by the student with her data collection instrument.
        - Number of data quality rules designed.

    :param url: The URL of the REDCap API
    :type url: str
    :param token: The token for authentication in the REDCap API
    :type token: str
    :return: The list of computed student indicators
    :rtype: list
    """
    project_id = get_project_id(url, token)
    project_name = get_project_name(url, token)
    student_dic = get_data_dictionary(url, token)
    number_of_fields = len(student_dic)
    completion_pct = compute_completion_pct(master_dic, student_dic)
    number_of_records = get_number_of_records(url, token)

    evaluation = [project_id, project_name, number_of_fields, completion_pct, number_of_records]

    return evaluation


def get_all_data_quality_rules(db_host, db_name, db_user, db_pass):
    """Retrieve all rows from the redcap_data_quality_rules database table.

    :param db_host: Database host
    :type db_host: str
    :param db_name: Database name
    :type db_name: str
    :param db_user: Database user
    :type db_user: str
    :param db_pass: Database password
    :type db_pass: str
    :return: A data frame with the table rows
    :rtype: DataFrame
    """
    engine = create_engine("mysql+pymysql://" + db_user + ":" + db_pass + "@" + db_host + "/" + db_name)
    dqr = pandas.read_sql("redcap_data_quality_rules", engine)

    return dqr


if __name__ == '__main__':
    URL = tokens.URL

    # Get MASTER data dictionary to be compared against students' dictionaries
    master_dic = get_data_dictionary(URL, tokens.API_TOKEN_20[0])

    grades = []
    for api_token in tokens.API_TOKEN_20:
        # Compute student performance indicators
        student_eval = compute_student_performance(URL, api_token)
        grades.append(student_eval)

        # Download and store student data dictionary and quality rules
        download_data_dictionary(URL, api_token)

    df_columns = ["project_id", "project_name", "number_of_fields", "completion_pct", "number_of_records"]
    grades_df = pandas.DataFrame(grades, columns=df_columns)

    # Get redcap_data_quality_rules table and compute the number of rules created in the master and each student project
    grades_df["number_of_dqr"] = 0
    rules = get_all_data_quality_rules(tokens.DB_HOST, tokens.DB_NAME, tokens.DB_USER, tokens.DB_PASS)
    counts = rules['project_id'].value_counts()
    for pid, number_of_dqr in counts.items():
        grades_df.loc[grades_df.project_id == pid, 'number_of_dqr'] = number_of_dqr

    print(grades_df)

    # Write and store grades and student data quality rules into two files in dowloads folder
    grades_df.to_csv("downloads/mgh_2020_grades.csv", index=False)

    student_rules = rules[rules.project_id.isin(grades_df.project_id)]
    student_rules.to_csv("downloads/mgh_2020_dqr.csv", index=False)
