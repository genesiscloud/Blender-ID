"""HTML code."""

template = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>OAuth Integration Test authorization page</title>

    <style type='text/css'>
        html, body {
            font-family: Ubuntu, Verdana, sans-serif;
            font-size: 12pt;
            background-color: white;
            color: black;
        }
        
        section {
            width: 500px;
            margin-left: auto;
            margin-right: auto;
        
            border-radius: 10px;
            box-shadow: 10px 10px 30px rgba(0, 0, 0, 0.15);
        }
        
        article, h1 {
            border: 3px solid %s;
        }
        
        article {
            border-radius: 0 0 10px 10px;
            background-color: #fefefe;
        }
        
        h1 {
            border-radius: 10px 10px 0 0;
            margin-top: 50px;
            margin-bottom: 0;
            
            text-align: center;
            text-shadow: 2px 2px 5px rgba(0, 0, 0, 0.5);
            font-size: 200%%;
            
            background-color: #1750d2;
            color: white;
        }
        
        p {
            text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.15);
            margin: 30px 30px 10px 30px;
        }
        
        p.note {
            font-size: 70%%;
            color: #888;
        }
        
        p.note a:visited, p.note a:link {
            color: #888;
        }
    </style>
</head>

<body>
<section>
    <h1>OAuth Integration Test Authorization</h1>
    <article>
        %s
    </article>
</section>
</body>

</html>
"""

auth_okay_html = template % ('#1750d2', """
    <p>Authorization of the application with Blender ID was successful.
    You can now <strong>close this browser window</strong>, and return to the application.</p>
""")

error_html = template % ('#d25017', """
    <p>Authorization of the application with Blender ID was <strong>unsuccessful</strong>.
    You can now <strong>close this browser window</strong>, and return to the application.</p>
""")
