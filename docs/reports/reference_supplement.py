"""Verified supplemental literature and an audit of all fifteen supplied entries."""
from report_content import read,link,H,S,T


def supplement():
    refs=read('docs/reports/references.json')
    pages=[]
    pages.append(('Expanded Review of the Supplied Literature',[
        S('Attention, Pretraining and Adaptation'),
        'Vaswani et al. [14] provide the attention-based Transformer foundation. RoBERTa [15] emphasizes careful control of pretraining data and optimization. Together they support treating architecture, supervision and training condition as separate experimental variables. TheoryBERT uses the original base uncased BERT lineage, not RoBERTa, and its direct-versus-plan comparison changes both representation and supervised data.',
        'BioBERT [16] demonstrates domain-specific continued pretraining in biomedicine. The more recent ModernBERT legal adaptation study [24] supplies another domain-adaptation example. These works motivate domain sensitivity but do not imply that biomedical or legal data would improve automata reasoning. Neither corpus nor checkpoint family is used in the local experiments. A formal-language continued-pretraining study would need its own corpus, cost budget and held-out evaluation.',
        S('Vocabulary, Distillation and Compute'),
        'The publisher-indexed Efficient Token Augmented Fine-Tuning record [19] identifies token augmentation as an alternative to expensive continued pretraining. Its full experimental text was not accessible in this research pass, so the report does not infer its initialization recipe or reproduce its performance claims. The supplied venue acronym is corrected to CSDE. This distinction matters because a valid citation is not evidence that a method was implemented here.',
        'Ryu and Lee [20] study adversarial adaptation with distillation for domain shift. Linder\'s KTH thesis [21] studies vocabulary expansion through self-distillation across tokenizations. These are plausible future controls for preserving old behavior while learning domain terms. The completed plan run uses supervised token and literal-pointer losses, not teacher-distribution distillation. Its efficiency result comes from a small head over frozen features.',
        S('Formal Languages and Semantic Parsing'),
        'Deletang et al. [17] study neural generalization across formal-language task classes. Strobl et al. [18] organize transformer-expressivity results under their assumptions. Their relevance is a warning: success on finite generated examples does not establish unrestricted recognition or compositional generalization. TheoryBERT delegates execution to classical formal algorithms after a bounded learned interpretation.',
        'Locascio et al. [3] remain directly relevant to natural-language regex generation and the public-data lineage. Xu et al. [25] provide a separate semantic-parsing example over Wikidata. The latter uses another task, data source and model family. TheoryBERT does not use WikiWebQuestions, Wikidata, LLaMA or GPT as a hidden prediction path.',
        S('Peripheral Context and Scope'),
        'The visual-language study by Alper et al. [22] concerns implicit visual knowledge in language representations. It does not validate drawing DFA graphs. CyMapNER [23] concerns domain-specific named entity recognition, not automata construction. Both are verified references and useful broader context, but neither supplies implementation evidence for this prototype. None of the extra literature datasets is included in the local training totals.'
    ]))
    pages.append(('Supplemental Bibliography',[
        ('small','These numbers continue the comprehensive report bibliography. The eight-page manuscript independently numbers its selected sources by first citation order.'),
        *[('small',f"[{x['id']}] {x['text']}<br/>{link(x['url'],x['url'])}") for x in refs[13:]],
        ('small','TAFT metadata and abstract were checked in the publisher-indexed proceedings; the full IEEE paper was inaccessible. The audit on the following pages distinguishes verified metadata, corrected details and project relevance. Literature-only datasets and models are not project training inputs.')
    ]))
    audit=read('docs/reports/reference_audit.json')
    by_id={x['id']:x for x in refs}
    for number,records in enumerate([audit[:8],audit[8:]]):
        blocks=[('small','Supplied item numbers refer to the bibliography provided by the user. Report reference numbers refer to the comprehensive report. Verification checks identity and publication metadata; it does not imply a reproduced experiment.')]
        for a in records:
            source=by_id[a['reference']]
            blocks.append(('small',f"<b>Supplied [{a['provided']}] / report [{a['reference']}]: {a['status']}</b><br/>{source['text']}<br/>{a['note']} {link(source['url'],'Primary record')}"))
        blocks.append(('small','Checked 29 October 2026. The authors of cited works are not the authors of this project. The project author/institution block remains omitted because names were not supplied.'))
        pages.append((f"Reference Audit: Supplied Items {'1-8' if number==0 else '9-15'}",blocks))
    return pages
