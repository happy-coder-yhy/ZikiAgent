# Merge Field Dictionary Into API And Verifier Docs

The historical login-task-job field dictionary should not remain a standalone documentation entry. Interface-specific field meanings and sources belong next to the relevant operator APIs, while cross-interface validation rules, configuration gaps, and write-before-validation ordering belong in verifier documentation because those rules are independent of the API caller and expected to evolve.
