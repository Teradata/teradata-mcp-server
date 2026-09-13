# DBA Tools

**Dependencies**

Assumes Teradata >=17.20.


**DBA** tools:

- dba_userSqlList - returns a list of recently executed SQL for a user
- dba_tableSqlList - returns a list of recently executed SQL for a table
- dba_tableSpace - returns CurrentPerm table space 
- dba_databaseSpace - returns Space allocated, space used and percentage used for a database
- dba_databaseVersion - returns the database version information
- dba_resusageSummary - Get the Teradata system usage summary metrics by weekday and hour for each workload type and query complexity bucket.
- dba_flowControl - Get the Teradata system flow control metrics by day and hour
- dba_featureUsage - Get the user feature usage metrics
- dba_userDelay - Get the Teradata user delay metrics.
- dba_tableUsageImpact - measures the usage of a table / view by a user
- dba_sessionInfo - gets session information for a user

**DBA** prompts:

- dba_systemVoice - Has the assistant impersonate the Teradata system when asked about its own health/activity (kept as a prompt because `examples/app-voice-agent` fetches it via `prompts/get`)

The reporting workflows that used to live here as prompts (`dba_databaseHealthAssessment`, `dba_userActivityAnalysis`, `dba_tableArchive`, `dba_databaseLineage`, `dba_tableDropImpact`) are now [Agent Skills](../../skills/README.md) instead: `dba-dashboard`, `dba-user-activity-analysis`, `dba-table-archive-advisor`, `dba-table-lineage`, and `dba-table-drop-impact` respectively.

[Return to Main README](../../../../README.md)
