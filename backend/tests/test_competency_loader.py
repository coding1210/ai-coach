from app.competency.loader import load_competency_map


def test_map_loads_and_validates():
    cmap = load_competency_map()
    assert cmap.version
    assert len(cmap.domains) == 10
    assert len(cmap.all_competencies()) == 59


def test_weight_and_domain_lookup():
    cmap = load_competency_map()
    # RAG is critical (weight 5); every competency resolves to a domain + weight.
    assert cmap.weight_of("rag.chunking") == cmap.weight_scale["critical"] == 5
    assert cmap.domain_of("rag.chunking").id == "rag"
    for c in cmap.all_competencies():
        assert cmap.weight_of(c.id) >= 1
