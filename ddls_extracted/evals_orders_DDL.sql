/*
 * File: evals_orders_DDL.sql
 * Generated: 2026-06-26 14:03:57
 * Type: TABLE
 * Database: demo_user
 * Object: evals_orders
 * Size: 563 characters
 */

CREATE SET TABLE demo_user.evals_orders ,FALLBACK ,
     NO BEFORE JOURNAL,
     NO AFTER JOURNAL,
     CHECKSUM = DEFAULT,
     DEFAULT MERGEBLOCKRATIO,
     MAP = TD_MAP1
     (
      order_id INTEGER NOT NULL,
      customer_name VARCHAR(100) CHARACTER SET LATIN NOT CASESPECIFIC NOT NULL,
      order_date DATE FORMAT 'YY/MM/DD' NOT NULL,
      ship_date DATE FORMAT 'YY/MM/DD',
      amount DECIMAL(10,2) NOT NULL,
      product_category VARCHAR(50) CHARACTER SET LATIN NOT CASESPECIFIC NOT NULL,
      quantity INTEGER NOT NULL, 
PRIMARY KEY ( order_id ))
;