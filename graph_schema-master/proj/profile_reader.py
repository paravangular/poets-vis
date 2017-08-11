import pstats
p = pstats.Stats('profile.cprof')
p.strip_dirs().sort_stats('cumtime').print_stats()
