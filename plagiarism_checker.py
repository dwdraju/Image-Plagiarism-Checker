import os
import numpy 
from math import sqrt
from time import time
from queue import Queue
import subprocess
from tkinter import *
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageChops
from skimage.feature import match_template


Max_Img_Width = 640
Max_Img_Height = 640
RMS_THRESHOLD = 50
            
class PlagiarismChecker(Frame):
    
    def __init__(self, parent):
        Frame.__init__(self, parent, background="white")        
        self.parent = parent      
        self.parent.title('Image Plagiarism Checker')
        self.parent.resizable(False, False)
        
        self.body = Frame(self.parent)
        
        self.body.pack(padx = 10, pady = 10)
        w = 500
        h = 200

        sw = self.body.winfo_screenwidth()
        sh = self.body.winfo_screenheight()
        
        x = (sw - w)/2
        y = (sh - h)/2
        self.parent.geometry('%dx%d+%d+%d' % (w, h, x, y))
        
        #Label(self.body, text = 'Locate Directory:',fg="red",bg="white").grid(row = 0, column = 0) 
        self.body.configure(background="white")      
        self.default_directory = Entry(self.body, width = 30)
        self.default_directory.grid(row = 1, column = 0, sticky = 'e')
        self.default_directory.insert(1, '/home/server/Desktop/images')          
        self.browse_button = ttk.Button(self.body, text = 'Browse Folder',command = self.browse_directory)
        self.browse_button.grid(row = 1, column = 1, sticky = 'w')
                         
        self.start_button = ttk.Button(self.body, text = 'Start Checking',command = self.search_callback)
        self.start_button.grid(row = 2, column = 0, columnspan = 2)
        
        self.stop_button = ttk.Button(self.body, text = 'Stop Process',state = DISABLED,command = self.stop_callback)
        self.stop_button.grid(row = 2, column = 1, columnspan = 2)
        
        self.quit_button = ttk.Button(self.body, text = 'Quit',command = self.quit)
        self.quit_button.grid(row = 2, column = 2, columnspan = 2)
        
        self.image_count = ttk.Label(self.body, state=DISABLED,text = "")
        self.image_count.grid(row = 0, column = 0, columnspan = 3)
        
        self.plagarised_images = ttk.Treeview(self.body, column = ('plagarised'))
        self.plagarised_images.heading('#0', text = 'Original Image')        
        self.plagarised_images.column('#0', width = 200)
        self.plagarised_images.heading('plagarised', text = 'Plagarised Image')
        self.plagarised_images.column('plagarised', width = 200)
       
        self.status_frame = Frame(self.parent)
        self.status_frame.pack(fill = BOTH, expand = True)
        
        self.status_var = StringVar()
        self.status_label = ttk.Label(self.status_frame, textvariable = self.status_var)
        
        self.progress_var = DoubleVar()
        self.progressbar = ttk.Progressbar(self.status_frame, mode = 'determinate',
                                           variable = self.progress_var)
                     
    def browse_directory(self):
        path = filedialog.askdirectory(initialdir = self.default_directory.get())
        self.default_directory.delete(0, END)
        self.default_directory.insert(0, path)
    def stop_callback(self):        
        #self.quit()         
        self.plagarised_images.grid_forget() # clear previous results      
        for cache in self.plagarised_images.get_children(''):
            self.plagarised_images.delete(cache)  
    def search_callback(self):        
        self.start_time = time()
              
        try: # build list of all jpg image files in directory
            self.path = self.default_directory.get()
            images = list(entry for entry in os.listdir(self.path) if entry.endswith('.jpg'))
            image_count=len(images)
            image_count_text=("Total image is:"+ format(image_count))

            self.image_count.config(text = (image_count_text))
        except:
            messagebox.showerror(title = 'Invalid Directory',message = 'Invalid Search Directory:\n' + self.path)
            return        
        if len(images) < 2:
            messagebox.showerror(title = 'Not Enough Images',message = 'Need at least 2 images to analyze.')
            return
            
        self.queue = Queue() # queue of image img_queues to process
        for i in images:
            for j in images:
                if i != j:
                    self.queue.put((i, j))
                           
        self.plagarised_images.grid_forget() # clear previous results      
        for item in self.plagarised_images.get_children(''):
            self.plagarised_images.delete(item)               

        self.status_var.set('Beginning...')
        self.status_label.pack(side = BOTTOM, fill = BOTH, expand = True)
        self.progressbar.config(value = 0.0, maximum = self.queue.qsize())
        self.progressbar.pack(side = BOTTOM, fill = BOTH, expand = True)
        self.browse_button['state']='disabled'
        self.start_button['state']='disabled'
        self.stop_button['state']='enabled'
              
        self.parent.after(10, self.start_operation) # provides time for tkinter to update GUI
        
    def start_operation(self):              
        img_queue = self.queue.get()          
        original = Image.open(os.path.join(self.path, img_queue[0]))
        template = Image.open(os.path.join(self.path, img_queue[1]))
        
        # verify that template image is larger than the original            
        if (template.size[0] < original.size[0]) and (template.size[1] < original.size[1]):
            
            # determine if images need to be resized smaller       
            if (original.size[0] > Max_Img_Width) or (original.size[1] > Max_Img_Height):         
                # calculate ratio for resizing
                ratio = min(Max_Img_Width/float(original.size[0]),
                            Max_Img_Height/float(original.size[1]))
                
                # resize images based on ratio   
                original = original.resize((int(ratio*original.size[0]),
                                            int(ratio*original.size[1])),
                                           Image.ANTIALIAS)
                template = template.resize((int(ratio*template.size[0]),
                                            int(ratio*template.size[1])),
                                           Image.ANTIALIAS)
            else:
                ratio = 1 # no resize was required
                   
            orig_arr = numpy.array(original.convert(mode = 'L'))
            temp_arr = numpy.array(template.convert(mode = 'L'))
            
            match_arr = match_template(orig_arr, temp_arr)        
            match_loc = numpy.unravel_index(numpy.argmax(match_arr), match_arr.shape)
          
            if ratio != 1: # if images were resized, get originals and calculate corresponding match_loc
                match_loc = (int(match_loc[0]/ratio), int(match_loc[1]/ratio))               
                original = Image.open(os.path.join(self.path, img_queue[0]))
                template = Image.open(os.path.join(self.path, img_queue[1]))
    
            # get matching subsection from original image (using RGB mode)                          
            orig_sub_arr = numpy.array(original)[match_loc[0]:match_loc[0] + template.size[0],
                                                 match_loc[1]:match_loc[1] + template.size[1]]
            orig_sub_img = Image.fromarray(orig_sub_arr, mode = 'RGB')           
           
            # calculate the root-mean-square difference between orig_sub_img and sub_img
            h_diff = ImageChops.difference(orig_sub_img, template).histogram()
            sum_of_squares = sum(value * ((idx % 256) ** 2) for idx, value in enumerate(h_diff))
            rms = sqrt(sum_of_squares/float(template.size[0]*template.size[1]))
                       
            if rms<RMS_THRESHOLD: # add matches to table
                
                self.plagarised_images.grid(row = 3, column = 0, columnspan = 2, padx = 5, pady = 5)
                self.plagarised_images.insert('', 'end', str(self.progress_var.get()),text = img_queue[0])#org
                self.plagarised_images.set(str(self.progress_var.get()), 'plagarised', img_queue[1]+format(rms))
                self.plagarised_images.config(height = len(self.plagarised_images.get_children('')))
                

        self.progressbar.step()   
        self.status_var.set('Analyzed {} vs {} \n {} img_queues remaining...'.format(img_queue[0], img_queue[1], self.queue.qsize()))            
        
        if not self.queue.empty():
            self.parent.after(10, self.start_operation)
        else:
            self.progressbar.pack_forget()
            self.browse_button['state']='enabled'
            self.start_button['state']='enabled'           
            elapsed_time = time() - self.start_time

            self.status_var.set('Done - Elapsed Time: {0:.2f} seconds'.format(elapsed_time))
                            
def main():    
    app = Tk()
    PlagiarismChecker(app)
    app.mainloop()
    
if __name__ == "__main__": main()

#Referenced from Python Code Clinic on lynda.com
