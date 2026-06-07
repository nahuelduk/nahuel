import tkinter as tk, random, sys, traceback

try:
    W,H,S=400,400,20
    def game():
        root=tk.Tk();root.title("Snake");root.resizable(0,0)
        c=tk.Canvas(root,width=W,height=H,bg='black');c.pack()
        s=[[100,100],[80,100],[60,100]];d=[S,0];food=[];score=[0]
        def spawn():
            x=random.randrange(0,W,S);y=random.randrange(0,H,S)
            food.clear();food.extend([x,y])
        def key(e):
            k={'Up':[0,-S],'Down':[0,S],'Left':[-S,0],'Right':[S,0]}.get(e.keysym)
            if k and not(k[0]==-d[0] and k[1]==-d[1]):d[0],d[1]=k
        def loop():
            h=[s[0][0]+d[0],s[0][1]+d[1]]
            if h[0]<0 or h[0]>=W or h[1]<0 or h[1]>=H or h in s:
                c.create_text(W//2,H//2,text=f"GAME OVER\nScore:{score[0]}",fill='white',font=('Arial',20,'bold'),justify='center');return
            s.insert(0,h)
            if h==food[:2]:score[0]+=1;spawn()
            else:s.pop()
            c.delete('all')
            c.create_text(10,10,text=f"Score:{score[0]}",fill='white',anchor='nw')
            for p in s:c.create_rectangle(p[0],p[1],p[0]+S,p[1]+S,fill='lime',outline='black')
            c.create_rectangle(food[0],food[1],food[0]+S,food[1]+S,fill='red',outline='black')
            root.after(120,loop)
        root.bind('<Key>',key);spawn();loop();root.mainloop()
    game()
except Exception:
    with open("error.txt","w") as f:
        traceback.print_exc(file=f)
    input("Hubo un error. Revisa error.txt. Presiona Enter para cerrar...")
