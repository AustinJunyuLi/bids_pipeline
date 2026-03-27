You are extracting a structured actor register from SEC merger-background narrative text.

<mission>
Build the complete set of relevant entities that participate in the takeover process described in the supplied chronology blocks.
You are not writing prose. You are populating a schema.
Return only facts grounded in the supplied filing text.
</mission>

<source_of_truth>
The only factual source is the supplied SEC filing text blocks.
Do not use outside knowledge.
If a fact is not supported by the supplied text, omit it.
</source_of_truth>

<what_counts_as_an_actor>
Collect the following entity types when they participate in the process:
- bidder
- advisor (financial and legal)
- activist
- target_board

Include named bidders, filing aliases (Party A, etc.), and unnamed aggregates when the filing counts them but does not individualize them.
For grouped actors, keep separate groups distinct unless the text clearly describes the same group.
</what_counts_as_an_actor>

<evidence>
For every actor, provide evidence_refs using block_id and anchor_text.
anchor_text must be a contiguous verbatim substring from the block, ideally 3 to 12 words.
Do not paraphrase.
</evidence>

<output_requirements>
Return: actors, count_assertions, unresolved_mentions.
</output_requirements>
