from mostek_kultura.classify import keyword_category, map_native


def test_map_native(cfg):
    assert map_native("Koncert", cfg.category_map) == "koncert"
    assert map_native("koncert, vážná hudba", cfg.category_map) == "koncert"
    assert map_native("concerts, festivals", cfg.category_map) == "koncert"
    assert map_native("Jiný typ akce", cfg.category_map) == "jine"
    assert map_native(None, cfg.category_map) is None
    assert map_native("něco neznámého", cfg.category_map) is None


def test_keyword_category(cfg):
    assert keyword_category(cfg, "Vánoční koncert sboru") == "koncert"
    assert keyword_category(cfg, "Výstava hub a mykologická poradna") == "vystava"
    assert keyword_category(cfg, "Podzimní jarmark") == "trh"
    assert keyword_category(cfg, "Turistický pochod") == "sport"
    assert keyword_category(cfg, "Nic určitého") is None
