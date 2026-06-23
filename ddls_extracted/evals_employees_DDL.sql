/*
 * File: evals_employees_DDL.sql
 * Generated: 2026-06-23 14:16:55
 * Type: TABLE
 * Database: demo_user
 * Object: evals_employees
 * Size: 572 characters
 */

CREATE SET TABLE demo_user.evals_employees ,FALLBACK ,
     NO BEFORE JOURNAL,
     NO AFTER JOURNAL,
     CHECKSUM = DEFAULT,
     DEFAULT MERGEBLOCKRATIO,
     MAP = TD_MAP1
     (
      employee_id INTEGER NOT NULL,
      name VARCHAR(100) CHARACTER SET LATIN NOT CASESPECIFIC NOT NULL,
      department VARCHAR(50) CHARACTER SET LATIN NOT CASESPECIFIC NOT NULL,
      salary DECIMAL(10,2),
      region VARCHAR(50) CHARACTER SET LATIN NOT CASESPECIFIC NOT NULL,
      hire_date DATE FORMAT 'YY/MM/DD' NOT NULL,
      manager_id INTEGER, 
PRIMARY KEY ( employee_id ))
;