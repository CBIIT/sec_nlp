# SEC NLP Integration

This repository contains scripts and resources for Natural Language Processing (NLP) and Machine Learning (ML) exploration as part of the Structured Eligibility Criteria (SEC) project. It is designed to be integrated with the main [SEC ETL](https://gitub.com/CBIIT/sec_etl) pipeline as a submodule, similar to the [SEC POC](https://github.com/CBIIT/sec_poc) repository.

## Overview

This repository's primary contributions to the SEC ETL are:

- **`sec_poc_tokenizer.py`**: Tokenizes eligibility criteria text into structured components.
- **`sec_poc_classifier.py`**: Classifies tokenized criteria by mapping them to NCIt (NCI Thesaurus) concepts.
- **`sec_poc_expression_generator.py`**: Generates logical expressions from classified criteria, enabling automated evaluation of patient eligibility against clinical trial requirements.

These scripts are integrated into the ETL pipeline and are not intended to be run in isolation.

Other files in this repository serve as ETL utilities, support experimentation, or are used by the SEC database schema for NLP-related processing (e.g., `nlp_schema.sql`).

## Development & Usage

### Local Development

1. **Clone the SEC ETL repository** and ensure this repo is included as a submodule.
2. **Install dependencies** as required by the ETL and this repo (see `requirements.txt`).
3. **Database Setup:**
   - The `nlp_schema.sql` file should be loaded as part of the SEC database schema initialization.
   - See the [SEC POC README](https://github.com/CBIIT/sec_poc) and [ETL documentation](https://github.com/CBIIT/sec_etl) for details on setting up the database and environment variables.
4. **Run ETL jobs** as described in the main ETL repo. The scripts here are invoked as part of those workflows.

### Production Deployment

- Code and schema changes from this repo are deployed as part of the overall SEC ETL deployment process.
- Do not run scripts here directly in production; always use the ETL pipeline.
- For deployment and environment configuration, refer to the [SEC POC](https://github.com/CBIIT/sec_poc) and [ETL](https://github.com/CBIIT/sec_etl) documentation.

## Best Practices

- **Schema changes** the relations defined in [nlp_schema.sql](./nlp_schema.sql) are a critical piece of the SEC POC system. Any changes affecting it or other aspects of the secapp schema should be coordinated with the rest of the codebase to ensure compatibility.
