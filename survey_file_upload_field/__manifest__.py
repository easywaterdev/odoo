# -*- coding: utf-8 -*-
{
    "name": "Survey File Upload Field",
    "summary": "Survey Multi File Upload Field and upload in attachment",
    "description": "Survey Multi File Upload Field and upload in attachment",

    'author': 'iPredict IT Solutions Pvt. Ltd.',
    'website': 'http://ipredictitsolutions.com',
    'support': 'ipredictitsolutions@gmail.com',

    'category': 'Survey',
    'version': '15.0.0.1.3',
    "depends": ["survey"],

    "data": [
        "security/ir.model.access.csv",
        "views/survey_question_views.xml",
        "views/survey_user_input_views.xml",
        "views/survey_templates.xml",
    ],

    'assets': {
        'web.assets_backend': [
            'survey_file_upload_field/static/src/css/survey_result.css',
        ],
        'survey.survey_assets': [
            'survey_file_upload_field/static/src/css/survey_front_result.css',
            'survey_file_upload_field/static/src/js/survey_form.js',
        ],
    },

    'license': "OPL-1",
    'price': 11,
    'currency': "EUR",

    "auto_install": False,
    "installable": True,

    'images': ['static/description/main.png'],
    'pre_init_hook': 'pre_init_check',
}
