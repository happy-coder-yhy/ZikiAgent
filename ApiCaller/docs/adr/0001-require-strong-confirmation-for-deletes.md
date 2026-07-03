# Require Strong Confirmation for Deletes

Destructive platform operations are exposed for administrator workflows, including future Agent-callable tools, but deletion must be confirmed outside the thin HTTP caller with a fixed phrase containing the resource type and ID. This preserves complete API coverage while preventing a model or simple yes/no prompt from accidentally deleting real platform resources.
