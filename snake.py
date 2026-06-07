import curses,random
def main(s):
    curses.curs_set(0);s.timeout(100)
    H,W=20,40;w=curses.newwin(H,W,0,0);w.keypad(1)
    b=[[H//2,W//4+i] for i in range(3)];d=[0,1];sc=0
    f=[random.randint(1,H-2),random.randint(1,W-2)]
    while 1:
        w.clear();w.border()
        w.addstr(f[0],f[1],'*')
        for i,p in enumerate(b):w.addstr(p[0],p[1],'#' if i else '@')
        w.addstr(0,2,f' Score:{sc} ')
        k=w.getch()
        nd={curses.KEY_UP:[-1,0],curses.KEY_DOWN:[1,0],curses.KEY_LEFT:[0,-1],curses.KEY_RIGHT:[0,1]}.get(k,d)
        if nd[0]!=-d[0] or nd[1]!=-d[1]:d=nd
        h=[b[0][0]+d[0],b[0][1]+d[1]]
        if h[0] in(0,H-1) or h[1] in(0,W-1) or h in b:
            w.addstr(H//2,W//2-4,'GAME OVER');w.refresh();curses.napms(2000);return
        b.insert(0,h)
        if h==f:sc+=1;f=[random.randint(1,H-2),random.randint(1,W-2)]
        else:b.pop()
        w.refresh()
curses.wrapper(main)
