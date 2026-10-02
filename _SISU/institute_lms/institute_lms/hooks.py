app_name = "institute_lms"
app_title = "Sisu · Institute LMS"
app_publisher = "Institute LMS contributors"
app_description = "Institute classrooms, schedules, payments and communication"
app_email = "admin@example.com"
app_license = "AGPL-3.0"
required_apps = ["lms"]
role_home_page = {"Institute Student": "campus", "Institute Teacher": "campus", "Institute Admin": "campus"}
after_install = "institute_lms.setup.after_install"
after_migrate = "institute_lms.setup.add_indexes"
website_route_rules = [{"from_route": "/campus", "to_route": "campus"}]
scheduler_events = {"cron": {"*/5 * * * *": ["institute_lms.notifications.dispatch", "institute_lms.notifications.dispatch_email", "institute_lms.calendar_sync.dispatch"]},
                    "daily": ["institute_lms.billing.daily", "institute_lms.retention.purge_expired_promotions", "institute_lms.profiles.purge_updates"]}
doc_events = {"IL Institute": {"validate": "institute_lms.validation.validate_institute"},
              "IL Session": {"on_update":"institute_lms.calendar_sync.session_changed"},
              "IL Enrollment": {"on_update":"institute_lms.calendar_sync.enrollment_changed"}}
add_to_apps_screen = [{"name": "institute_lms", "title": "Sisu", "route": "/campus",
                       "logo": "/assets/institute_lms/brand.svg"}]

on_session_creation = "institute_lms.portal_policy.stamp_session"
on_login = "institute_lms.portal_policy.validate_login"
