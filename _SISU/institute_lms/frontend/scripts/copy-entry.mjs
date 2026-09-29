import { readFileSync, writeFileSync, mkdirSync } from 'node:fs'
mkdirSync('../institute_lms/www', { recursive: true })
const html = readFileSync('../institute_lms/public/portal/index.html', 'utf8')
writeFileSync('../institute_lms/www/campus.html', html)
