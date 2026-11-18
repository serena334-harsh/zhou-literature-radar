import copy
import unittest
from update_public import candidate,apply_candidates,arxiv_entries,crossref_items,direction

class PublicFeedTests(unittest.TestCase):
    def test_healthcare_is_excluded(self):
        self.assertIsNone(direction('Remote implementation of community healthcare'))
        self.assertEqual(direction('Remote implementation of unitary operations'),'远程量子操作 RIO')
    def test_version_preserves_human_work(self):
        p=candidate('Remote implementation of quantum operations','A','远程量子操作 RIO','2026-11-18')
        p.update(id='arxiv:2610.12345',arxiv='2610.12345',version='v1 · 预印本',summary='人工核验摘要')
        data={'papers':[p]};new=copy.deepcopy(p);new.update(version='v2 · 预印本',updated='2026-11-18',summary='机器候选')
        changes=apply_candidates(data,[new],'2026-11-18')
        self.assertEqual(len(changes),1);self.assertEqual(p['summary'],'人工核验摘要');self.assertEqual(p['version'],'v2 · 预印本')
        self.assertEqual(apply_candidates(data,[new],'2026-11-19'),[])
    def test_doi_assignment_deduplicates(self):
        p=candidate('Remote state preparation','A','远程态制备 RSP','2026-11-18');p.update(id='stable',arxiv='2610.12345',version='v1')
        new=copy.deepcopy(p);new.update(id='doi:10.1234/example',doi='10.1234/example')
        data={'papers':[p]};apply_candidates(data,[new],'2026-11-18')
        self.assertEqual(len(data['papers']),1);self.assertEqual(p['id'],'stable');self.assertEqual(p['doi'],'10.1234/example')
    def test_abstract_is_not_republished(self):
        raw=b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/2610.12345v1</id><title>Remote state preparation</title><summary>UNIQUE RAW ABSTRACT TEXT</summary><published>2026-11-18T00:00:00Z</published><updated>2026-11-18T00:00:00Z</updated><author><name>A</name></author></entry></feed>'''
        self.assertNotIn('UNIQUE RAW ABSTRACT TEXT',str(arxiv_entries(raw,'2026-11-18')))

if __name__=='__main__':unittest.main()
