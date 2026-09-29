// Display labels, not an equivalence or admissions framework. Local names can be added.
const group = (category, labels, keywords = '') => labels.map(label => ({label, category, keywords}))
export const educationLevels = [
  ...group('Education stages', ['Early childhood / preschool', 'Kindergarten / reception', 'Primary education', 'Lower secondary education', 'Upper secondary education', 'Post-secondary education', 'Short-cycle tertiary education', 'Undergraduate education', 'Postgraduate education', 'Doctoral education'], 'global international school college university'),
  ...group('School grades & years', Array.from({length:13}, (_,i)=>`Grade ${i+1}`), 'school class standard elementary secondary high school'),
  ...group('School grades & years', Array.from({length:13}, (_,i)=>`Year ${i+1}`), 'school primary secondary'),
  ...group('International programmes', ['Cambridge Early Years', 'Cambridge Primary', 'Cambridge Lower Secondary', 'Cambridge IGCSE', 'Cambridge O Level', 'Cambridge International AS Level', 'Cambridge International A Level'], 'british uk international'),
  ...group('International programmes', ['Pearson Edexcel iPrimary', 'Pearson Edexcel iLowerSecondary', 'Pearson Edexcel International GCSE', 'Pearson Edexcel International AS Level', 'Pearson Edexcel International A Level', 'Pearson BTEC International Level 2', 'Pearson BTEC International Level 3'], 'british uk international edexcel'),
  ...group('International programmes', ['IB Primary Years Programme (PYP)', 'IB Middle Years Programme (MYP)', 'IB Diploma Programme (DP)', 'IB Career-related Programme (CP)'], 'international baccalaureate'),
  ...group('Sri Lanka', ['Sri Lanka Grade 5 Scholarship', 'Sri Lanka G.C.E. O/L', 'Sri Lanka G.C.E. A/L'], 'sri lankan local syllabus ordinary advanced shishyathwa ශිෂ්‍යත්ව සාමාන්‍ය උසස්'),
  ...group('Middle East', ['UAE Cycle 1', 'UAE Cycle 2', 'UAE Cycle 3 — General', 'UAE Cycle 3 — Advanced'], 'united arab emirates dubai abu dhabi moE middle east arabic الإمارات'),
  ...group('University & higher education', ['Foundation / university preparation', 'Certificate', 'Diploma', 'Higher diploma', 'Higher National Diploma (HND)', 'Associate degree', 'Bachelor’s degree', 'Bachelor’s honours degree', 'Graduate certificate', 'Postgraduate diploma', 'Master’s degree', 'Professional degree', 'Doctorate / PhD'], 'university college higher tertiary undergraduate postgraduate degree bachelors masters'),
  ...group('Vocational & lifelong learning', ['Technical / vocational training (TVET)', 'Apprenticeship', 'Professional certification', 'Continuing professional development (CPD)', 'Adult education', 'Language course', 'Short course', 'Online course', 'Independent learning / homeschool'], 'skills trade training distance learning all ages'),
]
export function searchEducation(query, category='') {
  const normalize=value=>value.toLocaleLowerCase().replace(/a\/l/g,'a level').replace(/o\/l/g,'o level')
  const words=normalize(query).trim().split(/\s+/).filter(Boolean)
  return educationLevels.filter(row=>(!category||row.category===category)&&words.every(word=>normalize(`${row.label} ${row.category} ${row.keywords}`).includes(word)))
}
