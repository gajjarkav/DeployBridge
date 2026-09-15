import urllib.request
import json
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

icons = [
    "html5", "css3", "javascript", "python", "nodedotjs", "react", "nextdotjs", 
    "vuedotjs", "docker", "postgresql", "go", "rust"
]

svgs = []
for icon in icons:
    url = f"https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/{icon}.svg"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, context=ctx) as response:
            svg_content = response.read().decode('utf-8')
            # Extract the path from the svg
            path_start = svg_content.find('<path')
            path_end = svg_content.find('/>', path_start) + 2
            if path_end == 1:
                path_end = svg_content.find('</path>', path_start) + 7
            path = svg_content[path_start:path_end]
            
            svgs.append(path)
    except Exception as e:
        print(f"Failed to fetch {icon}: {e}")

html_parts = []
for path in svgs:
    html_parts.append(f"""
                <div class="flex items-center justify-center w-20 h-20 sm:w-28 sm:h-28 rounded-2xl bg-gradient-to-br from-[#1a1f2e] via-[#151925] to-[#0f121b] border border-gray-700/50 shadow-lg hover:border-db_primary/40 hover:scale-105 transition-all duration-300 shrink-0 group">
                    <svg class="w-10 h-10 sm:w-14 sm:h-14 shrink-0 text-gray-300 group-hover:text-white transition-colors duration-300" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                        {path}
                    </svg>
                </div>""")

# Also add GitHub and Render that the user wants
github_path = '<path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/>'
render_path = '<path d="M18.263.007c-3.121-.147-5.744 2.109-6.192 5.082-.018.138-.045.272-.067.405-.696 3.703-3.936 6.507-7.827 6.507-1.388 0-2.691-.356-3.825-.979a.2024.2024 0 0 0-.302.178V24H12v-8.999c0-1.656 1.338-3 2.987-3h2.988c3.382 0 6.103-2.817 5.97-6.244-.12-3.084-2.61-5.603-5.682-5.75"/>'

html_parts.insert(0, f"""
                <div class="flex items-center justify-center w-20 h-20 sm:w-28 sm:h-28 rounded-2xl bg-gradient-to-br from-[#1a1f2e] via-[#151925] to-[#0f121b] border border-gray-700/50 shadow-lg hover:border-db_primary/40 hover:scale-105 transition-all duration-300 shrink-0 group">
                    <svg class="w-10 h-10 sm:w-14 sm:h-14 shrink-0 text-gray-300 group-hover:text-white transition-colors duration-300" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                        {render_path}
                    </svg>
                </div>""")
                
html_parts.insert(0, f"""
                <div class="flex items-center justify-center w-20 h-20 sm:w-28 sm:h-28 rounded-2xl bg-gradient-to-br from-[#1a1f2e] via-[#151925] to-[#0f121b] border border-gray-700/50 shadow-lg hover:border-db_primary/40 hover:scale-105 transition-all duration-300 shrink-0 group">
                    <svg class="w-10 h-10 sm:w-14 sm:h-14 shrink-0 text-gray-300 group-hover:text-white transition-colors duration-300" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                        {github_path}
                    </svg>
                </div>""")


belt_content = "\n".join(html_parts)
with open('belt_svgs.html', 'w') as f:
    f.write(belt_content)
